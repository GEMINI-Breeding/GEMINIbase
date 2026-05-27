"""
Phase 9d': PGEN-based genomic ingest pipeline.

The wizard POSTs a single uploaded file (xlsx / HapMap / VCF) to the
ingest endpoint. This module:

  1. Transcodes the upload into a normalized VCF that ``plink2`` can
     consume. xlsx is parsed in-process; HapMap/VCF passes through with
     light fixups. Large files stream from disk; we never hold a full
     genotype matrix in memory.
  2. Runs ``plink2 --vcf … --make-pgen`` to produce the canonical PGEN
     trio (.pgen / .pvar / .psam) and ``bcftools view -O b`` to produce
     the BCF + .csi sidecar for region queries.
  3. Computes per-variant stats (n_called, n_missing, MAF, HWE) with a
     single ``plink2 --freq counts --hardy`` pass and packs them into
     ``stats.parquet`` via DuckDB if available, else CSV.
  4. Uploads every artefact to ``minio://gemini/genotyping/{study_id}/``
     and inserts metadata rows into the four Phase 9d' Postgres tables.

Returned shape mirrors the legacy ``GenotypeMatrixBatchResult`` so the
frontend wizard can keep its existing "X variants / Y records inserted"
display while we cut the storage layer over.

The legacy ``_ingest_matrix_impl`` in
``gemini/rest_api/controllers/genotyping_study.py`` continues to exist
unchanged — Phase 9d'.5 deletes it once the read paths have moved.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from gemini.api.base import minio_storage_provider
from gemini.db.core.base import db_engine
from gemini.db.models.accessions import AccessionModel
from gemini.db.models.genotyping_studies import GenotypingStudyModel
from gemini.db.models.genotyping_study_files import (
    ALLOWED_FILE_KINDS,
    GenotypingStudyFileModel,
)
from gemini.db.models.genotyping_study_samples import GenotypingStudySampleModel
from gemini.db.models.genotyping_study_variant_stats import (
    GenotypingStudyVariantStatsModel,
)
from gemini.db.models.genotyping_study_variants import GenotypingStudyVariantModel
from gemini.db.models.variants import VariantModel

logger = logging.getLogger(__name__)


MINIO_BUCKET = "gemini"
MINIO_PREFIX_FMT = "genotyping/{study_id}/"

# IUPAC genotype-call regexes used to validate cells in xlsx ingest.
# Mirrors detection-engine.ts. We keep this lenient — anything that
# isn't recognised becomes "./" (missing) rather than failing the row.
_NULL_TOKENS = {"", "NA", "N/A", "na", ".", "--", "?", "NN"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class IngestResult:
    """Returned to the REST controller; mirrors the legacy batch-result
    shape so the frontend doesn't need a second consumer."""

    variants_inserted: int = 0
    records_inserted: int = 0
    samples_inserted: int = 0
    files: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def ingest_genotype_file(
    *,
    study_id: str,
    upload_path: Path,
    upload_filename: str,
    sample_canonical_map: Optional[dict[str, str]] = None,
    skipped_headers: Optional[list[str]] = None,
    created_accessions: Optional[list[str]] = None,
    experiment_name: Optional[str] = None,
    population_name: Optional[str] = None,
) -> IngestResult:
    """Top-level entry point. Called by the REST controller after the
    multipart upload has been written to ``upload_path``.

    Args:
        study_id: UUID of the GenotypingStudy this file is being ingested
            into. The study must already exist (the wizard creates it
            ahead of time so a back-button doesn't orphan rows).
        upload_path: Absolute path to the temp file holding the user's
            upload (xlsx/HapMap/VCF).
        upload_filename: Original filename, used both for format detection
            and for the ``source`` artefact key in MinIO.
        sample_canonical_map: ``raw_header → canonical_accession_name``
            from the wizard's sample-resolve step. Headers absent from
            the map are dropped.
        skipped_headers: Headers the user explicitly asked to skip.
        created_accessions: Canonical names that don't exist as accessions
            yet and should be created before ingest.
        experiment_name: Optional. When supplied alongside
            ``population_name``, ensures a Population row exists tied to
            this experiment and links every accession created during
            this ingest to it (mirrors the trait wizard's behavior).
        population_name: Optional. See ``experiment_name``.
    """
    sample_canonical_map = sample_canonical_map or {}
    skipped_headers = skipped_headers or []
    created_accessions = created_accessions or []

    result = IngestResult()
    study = _load_study(study_id)
    if study is None:
        raise ValueError(f"genotyping_study {study_id} not found")

    # 0. If a population was specified, ensure the Population row exists
    #    + is associated with the experiment. We do this up front so the
    #    accession-link step below has a target to point at.
    if population_name and experiment_name:
        from gemini.api.population import Population
        Population.create(
            population_name=population_name,
            experiment_name=experiment_name,
        )

    # 1. Accession backfill (formerly: bulk-created here in its own
    #    transaction). Moved into the main ingest transaction below so
    #    a downstream failure rolls the accession rows back instead of
    #    stranding them — the genomic ingest path used to be a primary
    #    source of accessions with no surviving link to any experiment.

    with tempfile.TemporaryDirectory(prefix=f"gemini-pgen-{study_id}-") as tmpdir:
        work = Path(tmpdir)
        # 2. Transcode upload → normalized VCF.
        vcf_path = work / "input.vcf"
        n_samples_in_file, n_variants_in_file = _transcode_to_vcf(
            upload_path=upload_path,
            upload_filename=upload_filename,
            out_vcf=vcf_path,
            sample_canonical_map=sample_canonical_map,
            skipped_headers=set(skipped_headers),
        )

        # 3. plink2 --vcf … --make-pgen
        out_prefix = work / "geno"
        _run_plink([
            "--vcf", str(vcf_path),
            "--make-pgen",
            "--out", str(out_prefix),
        ])
        pgen = out_prefix.with_suffix(".pgen")
        pvar = out_prefix.with_suffix(".pvar")
        psam = out_prefix.with_suffix(".psam")

        # 4. bcftools sort → BCF + .csi. We use ``sort`` (not ``view``)
        #    because some matrix uploads have cM-derived positions that
        #    aren't strictly increasing within a chromosome
        #    (BreedBase / DArT outputs sometimes interleave). Tabix
        #    indexing requires sorted positions, so we let bcftools
        #    do that pass — it streams and is essentially free.
        bcf = work / "geno.bcf"
        _run([
            "bcftools", "sort", "-O", "b", "-o", str(bcf), str(vcf_path),
        ])
        _run(["bcftools", "index", "--csi", str(bcf)])

        # 5. plink2 --freq counts --hardy → CSV → MinIO. Cheap; lets the
        #    variant browser show MAF/missing/HWE without unpacking PGEN.
        stats_path = work / "stats.csv"
        _compute_stats(
            pfile_prefix=out_prefix,
            out_csv=stats_path,
        )

        # 6. Upload everything to MinIO. Sweep the prefix first so a
        #    re-ingest doesn't leave orphan objects whose catalog row
        #    got overwritten (e.g. an older ``source`` file with a
        #    different basename).
        _sweep_study_prefix(study_id)
        prefix = MINIO_PREFIX_FMT.format(study_id=study_id)
        result.files["pgen"] = _upload(prefix + "geno.pgen", pgen)
        result.files["pvar"] = _upload(prefix + "geno.pvar", pvar)
        result.files["psam"] = _upload(prefix + "geno.psam", psam)
        result.files["bcf"] = _upload(prefix + "geno.bcf", bcf)
        result.files["bcf_index"] = _upload(prefix + "geno.bcf.csi", bcf.with_suffix(".bcf.csi"))
        result.files["parquet"] = _upload(prefix + "stats.csv", stats_path)
        result.files["source"] = _upload(prefix + upload_filename, upload_path)

        # 7. Postgres metadata. Variants and samples come from the .pvar
        #    and .psam (canonical PLINK output), not the upload — that's
        #    what guarantees the ordinals match the PGEN file.
        sample_names = _read_psam_samples(psam)
        variant_rows = list(_read_pvar_variants(pvar))
        result.samples_inserted = len(sample_names)
        result.variants_inserted = len(variant_rows)
        # records_inserted is variants × samples in the file (an upper
        # bound; nothing is stored as call rows any more, but the
        # frontend's existing display still wants this number).
        result.records_inserted = result.variants_inserted * result.samples_inserted

        # Every accession we'll touch in this ingest: the wizard's
        # explicit `created_accessions` (names the user mapped to as
        # "create new") plus whatever names the .psam carries after
        # PLINK transcoding. The in-session ensure call below creates
        # both sets atomically with the study_samples rows, so a mid-
        # ingest failure rolls every new accession back too.
        ingest_accession_names = list({*created_accessions, *sample_names})

        with db_engine.get_session() as session:
            _upsert_files(session, study_id, result.files, work_dir=work)
            sample_id_by_name = _ensure_accessions_in_session(
                session, ingest_accession_names
            )
            variant_id_by_key = _ensure_variants_in_session(session, variant_rows)
            _upsert_study_samples(
                session, study_id, sample_names, sample_id_by_name
            )
            _upsert_study_variants(
                session, study_id, variant_rows, variant_id_by_key
            )
            stats_rows = _read_stats_csv(stats_path)
            _upsert_variant_stats(
                session, study_id, stats_rows, variant_rows, variant_id_by_key,
            )
            # Population link in-session so the M2M rows commit
            # together with the accessions and study_samples. Out-of-
            # transaction linkage (the previous code path) would
            # strand accessions if the link step failed after commit.
            if population_name:
                _associate_accessions_with_population_in_session(
                    session,
                    ingest_accession_names,
                    population_name,
                )
            session.commit()

        # Sanity: counts in the file must match the declared sample map.
        if (
            sample_canonical_map
            and len(sample_names) > 0
            and len(sample_names) != len(set(sample_canonical_map.values()) - set(skipped_headers))
        ):
            result.errors.append(
                "sample-count mismatch between resolved map and PGEN .psam; "
                f"map kept {len(set(sample_canonical_map.values()))}, "
                f".psam has {len(sample_names)}"
            )

    return result


# ---------------------------------------------------------------------------
# Transcoding upload → normalized VCF
# ---------------------------------------------------------------------------


def _transcode_to_vcf(
    *,
    upload_path: Path,
    upload_filename: str,
    out_vcf: Path,
    sample_canonical_map: dict[str, str],
    skipped_headers: set[str],
) -> tuple[int, int]:
    """Detect the upload format and write a single VCF that plink2 can
    consume. Returns (n_samples, n_variants)."""
    ext = upload_filename.lower().rsplit(".", 1)[-1] if "." in upload_filename else ""
    if ext in ("xlsx", "xls", "ods"):
        return _transcode_xlsx(
            upload_path, out_vcf, sample_canonical_map, skipped_headers
        )
    if ext in ("hmp", "hapmap"):
        # plink2 handles HapMap natively; copy through and let the
        # caller invoke plink with --import-hapmap. For now we go via
        # bcftools which doesn't, so we transcode HapMap → VCF here.
        return _transcode_hapmap(
            upload_path, out_vcf, sample_canonical_map, skipped_headers
        )
    if ext in ("vcf", "vcf.gz", "bcf"):
        return _passthrough_vcf(
            upload_path, out_vcf, sample_canonical_map, skipped_headers
        )
    # CSV/TSV matrix — use the same logic as xlsx but without SheetJS.
    if ext in ("csv", "tsv", "txt"):
        return _transcode_delimited(
            upload_path, out_vcf, sample_canonical_map, skipped_headers
        )
    raise ValueError(f"unsupported genomic upload extension: .{ext}")


def _transcode_xlsx(
    src: Path,
    dst: Path,
    sample_canonical_map: dict[str, str],
    skipped_headers: set[str],
) -> tuple[int, int]:
    """xlsx matrix → VCF. Two-pass: pass 1 collects the contig set so
    we can emit ``##contig=<ID=…>`` lines (bcftools requires these even
    though plink2 doesn't). Pass 2 streams the body. ``read_only`` mode
    in openpyxl is forward-only iteration, so we materialise variant
    rows in memory; for the typical ~30 k-row breeding panel this is a
    few MB and well worth bcftools strictness."""
    import openpyxl  # type: ignore[import-untyped]

    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    sheet = wb.active
    rows_iter = sheet.iter_rows(values_only=True)

    header_row: list[str] | None = None
    for row in rows_iter:
        populated = sum(1 for c in row if c not in (None, ""))
        if populated >= 4:
            header_row = [str(c) if c is not None else "" for c in row]
            break
    if header_row is None:
        raise ValueError("could not find a header row in the xlsx (need ≥4 populated cells)")

    keep_idx, sample_names, variant_meta = _classify_matrix_columns(
        header_row, sample_canonical_map, skipped_headers
    )
    n_samples = len(sample_names)

    # Buffer rows + collect contigs. Skip rows that don't look like
    # variant rows so trailing trait/phenotype blocks (e.g. tpj13827)
    # don't get scanned as chromosomes.
    body_rows: list[list] = []
    contigs: list[str] = []
    seen: set[str] = set()
    chrom_idx = variant_meta.get("chromosome")
    alleles_idx = variant_meta.get("alleles")
    for row in rows_iter:
        if not row or all(c in (None, "") for c in row):
            continue
        cells = [c if c is not None else "" for c in row]
        body_rows.append(cells)
        if chrom_idx is None:
            continue
        chrom_val = cells[chrom_idx] if chrom_idx < len(cells) else ""
        chrom = str(chrom_val).strip() if chrom_val not in (None, "") else ""
        if not chrom:
            # Reject phenotype/trait rows whose chromosome and alleles
            # are both empty — they're not variants.
            if alleles_idx is None:
                continue
            a = cells[alleles_idx] if alleles_idx < len(cells) else ""
            if not (a and str(a).strip()):
                continue
            chrom = "0"
        if chrom not in seen:
            seen.add(chrom)
            contigs.append(chrom)
    if not contigs:
        contigs = ["0"]

    with dst.open("w", newline="") as out:
        _write_vcf_header(out, sample_names, contigs)
        n_variants = 0
        for cells in body_rows:
            line = _matrix_row_to_vcf(cells, keep_idx, variant_meta)
            if line:
                out.write(line + "\n")
                n_variants += 1
    return n_samples, n_variants


def _transcode_delimited(
    src: Path,
    dst: Path,
    sample_canonical_map: dict[str, str],
    skipped_headers: set[str],
) -> tuple[int, int]:
    """CSV/TSV matrix → VCF. Sniff delimiter from the first non-empty
    line, then look for the *first* row with ≥4 populated cells — that's
    the header (skipping any banner rows that precede it). All
    subsequent rows are body. Two-pass like _transcode_xlsx so bcftools
    gets ``##contig=`` declarations.

    Earlier this routine had a bug where the header-detect loop would
    consume the actual header into ``candidates`` and then misidentify
    the first data row as the header — only triggered on CSV inputs
    without a banner row.
    """
    with src.open(newline="") as fh:
        first = fh.readline()
        if not first.strip():
            raise ValueError("delimited file is empty")
        delim = "\t" if first.count("\t") > first.count(",") else ","
        first_cells = next(csv.reader([first], delimiter=delim))
        rows: Iterator[list[str]] = csv.reader(fh, delimiter=delim)

        header_row: list[str] | None
        if sum(1 for c in first_cells if c.strip()) >= 4:
            # First line is the header — common case for CSVs that
            # don't ship a banner row.
            header_row = first_cells
        else:
            # Banner row(s) precede the header. Scan forward until we
            # hit a row with ≥4 populated cells.
            header_row = None
            for cells in rows:
                if sum(1 for c in cells if c.strip()) >= 4:
                    header_row = cells
                    break
        if header_row is None:
            raise ValueError("delimited matrix has no header row with ≥4 populated cells")

        keep_idx, sample_names, variant_meta = _classify_matrix_columns(
            header_row, sample_canonical_map, skipped_headers
        )
        # Buffer rows + collect chromosomes (same reason as xlsx path).
        body_rows: list[list[str]] = []
        contigs: list[str] = []
        seen: set[str] = set()
        chrom_idx = variant_meta.get("chromosome")
        for cells in rows:
            if not cells or all(not c.strip() for c in cells):
                continue
            body_rows.append(cells)
            if chrom_idx is not None and chrom_idx < len(cells):
                c = cells[chrom_idx].strip() or "0"
                if c not in seen:
                    seen.add(c)
                    contigs.append(c)
        if not contigs:
            contigs = ["0"]

        with dst.open("w", newline="") as out:
            _write_vcf_header(out, sample_names, contigs)
            n_variants = 0
            for cells in body_rows:
                line = _matrix_row_to_vcf(cells, keep_idx, variant_meta)
                if line:
                    out.write(line + "\n")
                    n_variants += 1
        return len(sample_names), n_variants


def _classify_matrix_columns(
    header_row: list[str],
    sample_canonical_map: dict[str, str],
    skipped_headers: set[str],
) -> tuple[list[int], list[str], dict[str, int]]:
    """Pick out the metadata-vs-sample columns. Returns:
      keep_idx: column indices we yield calls for (in output order)
      sample_names: parallel list of canonical names for those columns
      variant_meta: maps "variant_name"|"chromosome"|"position"|"alleles"
                    → column index in the input row
    """
    variant_meta: dict[str, int] = {}
    for i, h in enumerate(header_row):
        hl = h.strip().lower()
        if hl in ("variant_name", "snp name", "snp_name", "rs", "rs#", "marker", "id"):
            variant_meta.setdefault("variant_name", i)
        elif hl in ("chromosome", "chrom", "chr", "#chrom"):
            variant_meta.setdefault("chromosome", i)
        elif hl in ("position", "pos", "bp", "cm", "map_pos", "map pos"):
            variant_meta.setdefault("position", i)
        elif hl in ("alleles", "snp_allele", "snp allele", "ref/alt"):
            variant_meta.setdefault("alleles", i)
        elif hl in ("design_sequence", "design seq", "design sequence"):
            variant_meta.setdefault("design_sequence", i)
    if "variant_name" not in variant_meta:
        raise ValueError(
            "matrix has no variant-name column (expected one of: variant_name, "
            "snp_name, rs#, marker, id)"
        )
    meta_cols = set(variant_meta.values())
    keep_idx: list[int] = []
    sample_names: list[str] = []
    for i, h in enumerate(header_row):
        if i in meta_cols:
            continue
        h_clean = h.strip()
        if not h_clean or h_clean in skipped_headers:
            continue
        canonical = sample_canonical_map.get(h_clean, h_clean)
        keep_idx.append(i)
        sample_names.append(canonical)
    return keep_idx, sample_names, variant_meta


def _matrix_row_to_vcf(
    cells: list,
    keep_idx: list[int],
    variant_meta: dict[str, int],
) -> Optional[str]:
    """Format one matrix row as a single VCF line.

    The matrix carries 2-letter IUPAC calls like ``"AA"``, ``"AG"``,
    ``"CC"`` (or numeric 0/1/2). We pick a consistent (REF, ALT)
    biallelic from the alleles column when present, else the first two
    distinct letters seen across calls. Calls become ``0/0``, ``0/1``,
    ``1/1``, or ``./.``.

    Returns None for rows that don't look like genotype variants — in
    practice this filters out trailing trait/phenotype rows that some
    supplements append to the bottom of the genotype matrix
    (the tpj13827 file is a real-world example with several
    "grain yield…" / "seed size…" rows after the last SNP).
    """
    name_idx = variant_meta["variant_name"]
    name = str(cells[name_idx] if name_idx < len(cells) else "").strip()
    if not name:
        return None
    # Reject rows whose chromosome / position / alleles columns are
    # all empty — those are extraneous trait rows, not variants.
    if "chromosome" in variant_meta:
        c = cells[variant_meta["chromosome"]] if variant_meta["chromosome"] < len(cells) else ""
        chrom_str = str(c).strip() if c is not None else ""
    else:
        chrom_str = ""
    has_alleles = False
    if "alleles" in variant_meta:
        a = cells[variant_meta["alleles"]] if variant_meta["alleles"] < len(cells) else ""
        has_alleles = bool(str(a).strip()) if a is not None else False
    if not chrom_str and not has_alleles:
        return None
    chrom = "0"
    if "chromosome" in variant_meta:
        c = cells[variant_meta["chromosome"]] if variant_meta["chromosome"] < len(cells) else ""
        chrom = str(c).strip() or "0" if c is not None else "0"
    pos = "1"
    if "position" in variant_meta:
        p = cells[variant_meta["position"]] if variant_meta["position"] < len(cells) else ""
        try:
            # cM gets multiplied to 1e6 to give plink something usable;
            # mirrors the workaround in workers/gwas/extract.py. VCF
            # POS is 1-based and bcftools indexing rejects 0 (and any
            # non-monotonic 0 → 1 transition), so we floor everything
            # at 1.
            pos_f = float(p) if str(p).strip() else 1.0
            if pos_f > 0 and pos_f < 1000:
                pos_f *= 1e6
            pos = str(max(1, int(pos_f)))
        except (ValueError, TypeError):
            pos = "1"
    ref, alt = "A", "G"
    if "alleles" in variant_meta:
        a = str(cells[variant_meta["alleles"]] if variant_meta["alleles"] < len(cells) else "").strip()
        if "/" in a:
            parts = a.split("/", 1)
            ref, alt = parts[0].strip()[:1] or "A", parts[1].strip()[:1] or "G"

    # Per-sample GT calls.
    gts: list[str] = []
    for i in keep_idx:
        raw = str(cells[i] if i < len(cells) else "").strip()
        gts.append(_call_to_gt(raw, ref, alt))

    return "\t".join([
        chrom, pos, name, ref, alt, ".", "PASS", ".", "GT", *gts
    ])


def _call_to_gt(raw: str, ref: str, alt: str) -> str:
    if raw in _NULL_TOKENS:
        return "./."
    s = raw.upper()
    if s in ("0",): return "0/0"
    if s in ("1",): return "0/1"
    if s in ("2",): return "1/1"
    if len(s) == 2 and s.isalpha():
        a, b = s[0], s[1]
        ref_u, alt_u = ref.upper(), alt.upper()
        n_alt = (a == alt_u) + (b == alt_u)
        if n_alt == 0 and (a == ref_u or b == ref_u):
            return "0/0"
        if n_alt == 1:
            return "0/1"
        if n_alt == 2:
            return "1/1"
    if len(s) == 1 and s.isalpha():
        # Single-letter call (homozygous shorthand).
        if s == alt.upper(): return "1/1"
        if s == ref.upper(): return "0/0"
    return "./."


def _write_vcf_header(
    out,
    sample_names: list[str],
    contigs: Optional[list[str]] = None,
) -> None:
    out.write("##fileformat=VCFv4.2\n")
    out.write("##source=gemini-pgen-ingest\n")
    out.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
    # bcftools requires ``##contig=<ID=…>`` for every chromosome that
    # appears in a body line — VCF spec recommends it; bcftools enforces
    # it on binary write. plink2 is fine without these declarations,
    # but our pipeline runs both, so we always emit them.
    for c in contigs or ["0"]:
        out.write(f"##contig=<ID={c}>\n")
    out.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t")
    out.write("\t".join(sample_names))
    out.write("\n")


def _transcode_hapmap(
    src: Path,
    dst: Path,
    sample_canonical_map: dict[str, str],
    skipped_headers: set[str],
) -> tuple[int, int]:
    """HapMap text → VCF. HapMap fixed columns: rs#, alleles, chrom,
    pos, strand, assembly#, center, protLSID, assayLSID, panelLSID,
    QCcode, then sample columns. Two-pass to collect ``##contig`` for
    bcftools."""
    HAPMAP_FIXED = 11
    with src.open() as fh:
        header = fh.readline().rstrip("\n").split("\t")
        if len(header) <= HAPMAP_FIXED:
            raise ValueError(f"HapMap header has only {len(header)} columns")
        sample_headers = header[HAPMAP_FIXED:]
        keep_idx: list[int] = []
        sample_names: list[str] = []
        for i, h in enumerate(sample_headers):
            h_clean = h.strip()
            if not h_clean or h_clean in skipped_headers:
                continue
            canonical = sample_canonical_map.get(h_clean, h_clean)
            keep_idx.append(i)
            sample_names.append(canonical)
        body_lines: list[list[str]] = []
        contigs: list[str] = []
        seen: set[str] = set()
        for line in fh:
            cols = line.rstrip("\n").split("\t")
            if len(cols) <= HAPMAP_FIXED:
                continue
            body_lines.append(cols)
            chrom = cols[2].strip() or "0"
            if chrom not in seen:
                seen.add(chrom)
                contigs.append(chrom)
        if not contigs:
            contigs = ["0"]
    with dst.open("w") as out:
        _write_vcf_header(out, sample_names, contigs)
        n_variants = 0
        for cols in body_lines:
            name = cols[0].strip()
            if not name:
                continue
            alleles = cols[1].strip()
            chrom = cols[2].strip() or "0"
            pos = cols[3].strip() or "0"
            ref, alt = "A", "G"
            if "/" in alleles:
                parts = alleles.split("/", 1)
                ref, alt = parts[0][:1] or "A", parts[1][:1] or "G"
            gts: list[str] = []
            for i in keep_idx:
                raw = cols[HAPMAP_FIXED + i] if HAPMAP_FIXED + i < len(cols) else ""
                gts.append(_call_to_gt(raw, ref, alt))
            out.write("\t".join([chrom, pos, name, ref, alt, ".", "PASS", ".", "GT", *gts]))
            out.write("\n")
            n_variants += 1
    return len(sample_names), n_variants


def _passthrough_vcf(
    src: Path,
    dst: Path,
    sample_canonical_map: dict[str, str],
    skipped_headers: set[str],
) -> tuple[int, int]:
    """VCF → VCF with sample-column rename + skip filter applied."""
    if not sample_canonical_map and not skipped_headers:
        # No-op rename; copy to dst directly.
        shutil.copyfile(src, dst)
        # Count variants + samples from the file.
        n_v, n_s = 0, 0
        with dst.open() as fh:
            for line in fh:
                if line.startswith("##"):
                    continue
                if line.startswith("#CHROM"):
                    n_s = max(0, len(line.rstrip("\n").split("\t")) - 9)
                else:
                    n_v += 1
        return n_s, n_v

    n_v = 0
    n_s = 0
    with src.open() as fh, dst.open("w") as out:
        for line in fh:
            if line.startswith("##"):
                out.write(line)
                continue
            if line.startswith("#CHROM"):
                cols = line.rstrip("\n").split("\t")
                fixed, sample_headers = cols[:9], cols[9:]
                keep_idx: list[int] = []
                renamed: list[str] = []
                for i, h in enumerate(sample_headers):
                    if h in skipped_headers:
                        continue
                    keep_idx.append(i)
                    renamed.append(sample_canonical_map.get(h, h))
                n_s = len(renamed)
                # Stash for body lines.
                body_keep = keep_idx
                out.write("\t".join(fixed + renamed) + "\n")
                continue
            cols = line.rstrip("\n").split("\t")
            fixed, sample_calls = cols[:9], cols[9:]
            keep = [sample_calls[i] for i in body_keep if i < len(sample_calls)]
            out.write("\t".join(fixed + keep) + "\n")
            n_v += 1
    return n_s, n_v


# ---------------------------------------------------------------------------
# plink2 + bcftools wrappers
# ---------------------------------------------------------------------------


def _run(cmd: list[str]) -> None:
    """Run an external command, raise on non-zero exit."""
    logger.info("running: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"command failed (exit {res.returncode}): {' '.join(cmd)}\n"
            f"stdout: {res.stdout[:2000]}\nstderr: {res.stderr[:2000]}"
        )


def _run_plink(args: list[str]) -> None:
    _run(["plink2", *args])


def _compute_stats(*, pfile_prefix: Path, out_csv: Path) -> None:
    """Run plink2 to emit per-variant freq and HWE stats, then merge
    them into a single CSV with columns
    (variant_name, n_called, n_missing, maf, hwe_p)."""
    base = pfile_prefix
    _run_plink([
        "--pfile", str(base),
        "--freq", "counts",
        "--missing", "variant-only",
        "--hardy", "midp",
        "--out", str(base) + ".stats",
    ])
    freq_path = Path(str(base) + ".stats.acount")
    miss_path = Path(str(base) + ".stats.vmiss")
    hwe_path = Path(str(base) + ".stats.hardy")
    freq = _read_plink_table(freq_path) if freq_path.exists() else {}
    miss = _read_plink_table(miss_path) if miss_path.exists() else {}
    hwe = _read_plink_table(hwe_path) if hwe_path.exists() else {}
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant_name", "n_called", "n_missing", "maf", "hwe_p"])
        for vname, frow in freq.items():
            n_alt = float(frow.get("ALT_CTS", "0"))
            obs = float(frow.get("OBS_CT", "0"))
            maf = (n_alt / obs) if obs > 0 else None
            if maf is not None and maf > 0.5:
                maf = 1.0 - maf
            mrow = miss.get(vname, {})
            n_missing = int(float(mrow.get("MISSING_CT", "0")) or 0)
            n_called = int(obs / 2) if obs > 0 else 0
            hrow = hwe.get(vname, {})
            hwe_p = hrow.get("P", None)
            try:
                hwe_p_f = float(hwe_p) if hwe_p not in (None, "", "NA") else None
            except (ValueError, TypeError):
                hwe_p_f = None
            w.writerow([
                vname,
                n_called,
                n_missing,
                f"{maf:.6f}" if maf is not None else "",
                f"{hwe_p_f:.6g}" if hwe_p_f is not None else "",
            ])


def _read_plink_table(p: Path) -> dict[str, dict[str, str]]:
    """Read a plink2 sumstats output file (tab-delimited with comment
    header). Returns dict keyed by ID column."""
    out: dict[str, dict[str, str]] = {}
    with p.open() as fh:
        header: list[str] = []
        for line in fh:
            if line.startswith("##"):
                continue
            cells = line.rstrip("\n").split("\t")
            if line.startswith("#"):
                header = [h.lstrip("#") for h in cells]
                continue
            if not header:
                continue
            row = dict(zip(header, cells))
            vid = row.get("ID") or row.get("SNP") or ""
            if vid:
                out[vid] = row
    return out


def _read_psam_samples(psam: Path) -> list[str]:
    """Read sample names from a PLINK2 .psam in file order.

    PLINK2 .psam has a header line starting with ``#`` that names the
    columns. Possible shapes:
      - ``#IID SEX`` (2 cols; modern PLINK2 default for VCF input)
      - ``#FID IID PAT MAT SEX PHENO1`` (6 cols; legacy / .fam-style)
    We look up the IID column index from the header rather than
    assuming a fixed offset.
    """
    out: list[str] = []
    iid_idx: Optional[int] = None
    with psam.open() as fh:
        for line in fh:
            if line.startswith("#"):
                cols = line.lstrip("#").rstrip("\n").split("\t")
                try:
                    iid_idx = cols.index("IID")
                except ValueError:
                    iid_idx = 0  # legacy headerless .fam-style
                continue
            cells = line.rstrip("\n").split("\t")
            if not cells:
                continue
            i = iid_idx if iid_idx is not None else 0
            if i < len(cells):
                out.append(cells[i])
    return out


def _read_pvar_variants(pvar: Path) -> Iterable[dict[str, str]]:
    """Read variant rows from a .pvar in file order."""
    header: list[str] = []
    with pvar.open() as fh:
        for line in fh:
            if line.startswith("##"):
                continue
            cells = line.rstrip("\n").split("\t")
            if line.startswith("#"):
                header = [c.lstrip("#") for c in cells]
                continue
            if not header:
                continue
            yield dict(zip(header, cells))


def _read_stats_csv(p: Path) -> list[dict[str, str]]:
    if not p.exists():
        return []
    with p.open() as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# MinIO + Postgres glue
# ---------------------------------------------------------------------------


def _upload(object_name: str, src: Path) -> str:
    """Upload one file to MinIO and return its s3-style URI."""
    minio_storage_provider.upload_file(
        object_name=object_name,
        input_file_path=src,
        bucket_name=MINIO_BUCKET,
    )
    return f"s3://{MINIO_BUCKET}/{object_name}"


def _file_kind_from_key(object_name: str) -> str:
    """Map a MinIO object name to one of ALLOWED_FILE_KINDS."""
    name = object_name.rsplit("/", 1)[-1]
    if name == "geno.pgen":
        return "pgen"
    if name == "geno.pvar":
        return "pvar"
    if name == "geno.psam":
        return "psam"
    if name == "geno.bcf":
        return "bcf"
    if name == "geno.bcf.csi":
        return "bcf_index"
    if name.endswith(".parquet") or name == "stats.csv":
        return "parquet"
    if name == "manifest.json":
        return "manifest"
    return "source"


def _load_study(study_id: str) -> Optional[GenotypingStudyModel]:
    with db_engine.get_session() as session:
        stmt = select(GenotypingStudyModel).where(
            GenotypingStudyModel.id == study_id
        )
        return session.execute(stmt).scalar_one_or_none()


def _associate_accessions_with_population(
    accession_names: list[str], population_name: str
) -> None:
    """Idempotent bulk-link accessions to a population.

    Mirrors ``Accession.associate_population`` but for many accessions
    in one transaction. Used by the genomic-import wizard so the user's
    chosen population groups every accession the wizard created
    (whether explicitly via ``created_accessions`` or implicitly via the
    .psam sample-name pass).

    Silently skips when the population doesn't exist or when the
    accession list is empty — both are no-op situations during normal
    operation.
    """
    if not accession_names or not population_name:
        return
    with db_engine.get_session() as session:
        _associate_accessions_with_population_in_session(
            session, accession_names, population_name
        )
        session.commit()


def _associate_accessions_with_population_in_session(
    session, accession_names: list[str], population_name: str
) -> None:
    """Same as :func:`_associate_accessions_with_population` but uses
    the caller's session and skips the commit, so the linkage rides
    along with whatever outer transaction is open. The ingest path uses
    this so accession + study_samples + population_accessions all
    commit atomically.
    """
    if not accession_names or not population_name:
        return
    from gemini.db.models.populations import PopulationModel
    from gemini.db.models.associations import PopulationAccessionModel
    from sqlalchemy import select as _select
    from sqlalchemy.dialects.postgresql import insert as _pg_insert

    pop = session.execute(
        _select(PopulationModel).where(
            PopulationModel.population_name == population_name
        )
    ).scalar_one_or_none()
    if pop is None:
        logger.warning(
            "Population %r does not exist; skipping accession link.",
            population_name,
        )
        return
    rows = session.execute(
        _select(AccessionModel.id, AccessionModel.accession_name).where(
            AccessionModel.accession_name.in_(accession_names)
        )
    ).all()
    if not rows:
        return
    payload = [
        {"population_id": pop.id, "accession_id": aid} for aid, _ in rows
    ]
    stmt = _pg_insert(PopulationAccessionModel.__table__).values(payload)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["population_id", "accession_id"]
    )
    session.execute(stmt)


def _ensure_accessions_in_session(
    session, names: list[str]
) -> dict[str, uuid.UUID]:
    """Return name→id, creating any missing rows."""
    if not names:
        return {}
    existing = session.execute(
        select(AccessionModel.id, AccessionModel.accession_name).where(
            AccessionModel.accession_name.in_(names)
        )
    ).all()
    out = {row.accession_name: row.id for row in existing}
    missing = [n for n in names if n not in out]
    if missing:
        new_rows = [
            {"id": uuid.uuid4(), "accession_name": n} for n in missing
        ]
        stmt = pg_insert(AccessionModel.__table__).values(new_rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["accession_name"])
        session.execute(stmt)
        # Re-query for ids (handles race + on-conflict skip).
        rows = session.execute(
            select(AccessionModel.id, AccessionModel.accession_name).where(
                AccessionModel.accession_name.in_(missing)
            )
        ).all()
        for row in rows:
            out[row.accession_name] = row.id
    return out


def _ensure_variants_in_session(
    session, variant_rows: list[dict[str, str]]
) -> dict[str, uuid.UUID]:
    """Create missing Variant rows; return variant_name → id."""
    names = [r["ID"] for r in variant_rows if r.get("ID")]
    if not names:
        return {}
    existing = session.execute(
        select(VariantModel.id, VariantModel.variant_name).where(
            VariantModel.variant_name.in_(names)
        )
    ).all()
    out = {row.variant_name: row.id for row in existing}
    missing = [r for r in variant_rows if r.get("ID") and r["ID"] not in out]
    if missing:
        payload = []
        for r in missing:
            try:
                chrom_int = int(float(r.get("CHROM", "0") or 0))
            except (ValueError, TypeError):
                chrom_int = 0
            try:
                pos_f = float(r.get("POS", "0") or 0)
            except (ValueError, TypeError):
                pos_f = 0.0
            payload.append({
                "id": uuid.uuid4(),
                "variant_name": r["ID"],
                "chromosome": chrom_int,
                "position": pos_f,
                "alleles": f"{r.get('REF', '')}/{r.get('ALT', '')}".strip("/"),
                "design_sequence": "",
                "variant_info": {},
            })
        stmt = pg_insert(VariantModel.__table__).values(payload)
        stmt = stmt.on_conflict_do_nothing(index_elements=["variant_name"])
        session.execute(stmt)
        rows = session.execute(
            select(VariantModel.id, VariantModel.variant_name).where(
                VariantModel.variant_name.in_([r["ID"] for r in missing])
            )
        ).all()
        for row in rows:
            out[row.variant_name] = row.id
    return out


def _sweep_study_prefix(study_id: str) -> None:
    """Remove every MinIO object under ``genotyping/{study_id}/``.

    Run before uploading fresh artefacts so re-ingest doesn't leave
    orphan objects from a previous run (e.g. an old ``source`` file
    whose name differs from the new one). Catalog-row drift was the
    cause of the lingering ``test_geno.xlsx`` in MinIO observed in
    the 9d'.6 wipe.
    """
    bucket = minio_storage_provider.bucket_name
    prefix = f"genotyping/{study_id}/"
    try:
        objs = list(minio_storage_provider.client.list_objects(
            bucket_name=bucket, prefix=prefix, recursive=True,
        ))
    except Exception:
        return
    for obj in objs:
        try:
            minio_storage_provider.client.remove_object(
                bucket_name=bucket, object_name=obj.object_name,
            )
        except Exception:
            # Best-effort: a leftover object is recoverable by the
            # study's `delete()` prefix sweep later.
            pass


def _upsert_files(
    session,
    study_id: str,
    files: dict[str, str],
    work_dir: Path,
) -> None:
    """Replace ``genotyping_study_files`` rows for this study."""
    session.execute(
        GenotypingStudyFileModel.__table__.delete().where(
            GenotypingStudyFileModel.study_id == study_id
        )
    )
    for kind, uri in files.items():
        local_name = uri.rsplit("/", 1)[-1]
        local = work_dir / local_name
        sha = _sha256_or_none(local) if local.exists() else None
        size = local.stat().st_size if local.exists() else None
        # Some "kinds" map to the same file_kind enum (e.g. several
        # internal source/manifest variants). Use the actual key.
        session.execute(
            pg_insert(GenotypingStudyFileModel.__table__).values(
                study_id=study_id,
                file_kind=kind if kind in ALLOWED_FILE_KINDS else "source",
                s3_uri=uri,
                bytes=size,
                sha256=sha,
            )
        )


def _sha256_or_none(p: Path) -> Optional[str]:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _upsert_study_samples(
    session,
    study_id: str,
    sample_names: list[str],
    sample_id_by_name: dict[str, uuid.UUID],
) -> None:
    session.execute(
        GenotypingStudySampleModel.__table__.delete().where(
            GenotypingStudySampleModel.study_id == study_id
        )
    )
    payload = []
    for ordinal, name in enumerate(sample_names):
        sid = sample_id_by_name.get(name)
        if sid is None:
            continue
        payload.append({
            "study_id": study_id,
            "accession_id": sid,
            "sample_index": ordinal,
        })
    if payload:
        session.execute(
            pg_insert(GenotypingStudySampleModel.__table__).values(payload)
        )


def _upsert_study_variants(
    session,
    study_id: str,
    variant_rows: list[dict[str, str]],
    variant_id_by_name: dict[str, uuid.UUID],
) -> None:
    session.execute(
        GenotypingStudyVariantModel.__table__.delete().where(
            GenotypingStudyVariantModel.study_id == study_id
        )
    )
    payload = []
    for ordinal, row in enumerate(variant_rows):
        name = row.get("ID")
        if not name:
            continue
        vid = variant_id_by_name.get(name)
        if vid is None:
            continue
        payload.append({
            "study_id": study_id,
            "variant_id": vid,
            "variant_index": ordinal,
        })
    if payload:
        session.execute(
            pg_insert(GenotypingStudyVariantModel.__table__).values(payload)
        )


def _upsert_variant_stats(
    session,
    study_id: str,
    stats_rows: list[dict[str, str]],
    variant_rows: list[dict[str, str]],
    variant_id_by_name: dict[str, uuid.UUID],
) -> None:
    session.execute(
        GenotypingStudyVariantStatsModel.__table__.delete().where(
            GenotypingStudyVariantStatsModel.study_id == study_id
        )
    )
    if not stats_rows:
        return
    payload = []
    for r in stats_rows:
        name = r.get("variant_name", "")
        vid = variant_id_by_name.get(name)
        if vid is None:
            continue

        def _f(v):
            try:
                return float(v) if v not in (None, "", "NA") else None
            except (ValueError, TypeError):
                return None

        def _i(v):
            try:
                return int(float(v)) if v not in (None, "", "NA") else None
            except (ValueError, TypeError):
                return None

        payload.append({
            "study_id": study_id,
            "variant_id": vid,
            "n_called": _i(r.get("n_called")),
            "n_missing": _i(r.get("n_missing")),
            "maf": _f(r.get("maf")),
            "hwe_p": _f(r.get("hwe_p")),
        })
    if payload:
        session.execute(
            pg_insert(GenotypingStudyVariantStatsModel.__table__).values(payload)
        )
