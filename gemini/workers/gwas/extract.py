"""
Extract genotype + phenotype data from the GEMINI DB and write PLINK1-format
binary filesets (.bed/.bim/.fam) plus a .pheno file for GEMMA.

PLINK .bed format reference:
- 3-byte header: 0x6c 0x1b 0x01  (magic, magic, variant-major mode)
- Per variant: ceil(n_samples/4) bytes; 4 samples per byte, 2 bits each, LSB first.
  Codes: 00 = hom A1, 01 = missing, 10 = het, 11 = hom A2.

Allele convention used here: Variant.alleles is stored as "ref/alt".
We assign A1 = alt, A2 = ref so that GEMMA's beta is the effect of the alt
(minor) allele relative to the reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Optional
from uuid import UUID

import numpy as np
from sqlalchemy import select

from gemini.db.core.base import db_engine
from gemini.db.models.accessions import AccessionModel
from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
from gemini.db.models.variants import VariantModel
from gemini.db.models.views.plot_accession_view import PlotAccessionViewModel
from gemini.db.models.views.trait_records_immv import TraitRecordsIMMVModel

# 2-bit PLINK codes
CODE_HOM_A1 = 0b00
CODE_MISSING = 0b01
CODE_HET = 0b10
CODE_HOM_A2 = 0b11


@dataclass(frozen=True)
class PlinkPaths:
    bed: Path
    bim: Path
    fam: Path
    samples: list[str]   # accession_name order used in .fam
    variants: list[dict]  # variant metadata in .bim row order


def _encode_call(call_value: Optional[str], a1: str, a2: str) -> int:
    """Encode a diploid call string into a PLINK 2-bit code.

    Args:
        call_value: Typically 2-char string like "TT", "CC", "TC", "NN", "--",
            or None for missing.
        a1: Effect allele (column 5 of .bim). We map this to alt.
        a2: Other allele (column 6 of .bim). We map this to ref.

    Returns:
        One of CODE_HOM_A1, CODE_MISSING, CODE_HET, CODE_HOM_A2.
    """
    if not call_value:
        return CODE_MISSING
    s = call_value.strip().upper()
    if len(s) != 2 or "N" in s or "-" in s or "." in s:
        return CODE_MISSING
    a, b = s[0], s[1]
    a1u, a2u = a1.upper(), a2.upper()
    if a == a1u and b == a1u:
        return CODE_HOM_A1
    if a == a2u and b == a2u:
        return CODE_HOM_A2
    if {a, b} == {a1u, a2u}:
        return CODE_HET
    return CODE_MISSING


def _pack_variant_row(codes: np.ndarray) -> bytes:
    """Pack one variant's per-sample codes into PLINK .bed bytes.

    Samples are packed 4-per-byte, sample 0 in the lowest 2 bits.
    The final byte is padded with CODE_MISSING for alignment.
    """
    n = codes.shape[0]
    pad = (4 - n % 4) % 4
    if pad:
        codes = np.concatenate([codes, np.full(pad, CODE_MISSING, dtype=np.uint8)])
    # Reshape to (n_bytes, 4), then bit-pack.
    grouped = codes.reshape(-1, 4).astype(np.uint8)
    packed = (
        grouped[:, 0]
        | (grouped[:, 1] << 2)
        | (grouped[:, 2] << 4)
        | (grouped[:, 3] << 6)
    ).astype(np.uint8)
    return packed.tobytes()


def write_plink_fileset(
    study_id: UUID | str,
    study_name: str,
    out_dir: Path,
    basename: str = "geno",
) -> PlinkPaths:
    """Stream all GenotypeRecord rows for a study and write a PLINK fileset.

    Memory footprint: one uint8 array of shape (n_variants, n_samples). For
    32k × 310 that is ~10 MB — comfortably in-memory.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with db_engine.get_session() as session:
        # 1. Samples — distinct accessions that appear in this study's records,
        #    sorted by accession_name for stable .fam order.
        sample_rows = session.execute(
            select(AccessionModel.id, AccessionModel.accession_name)
            .where(
                AccessionModel.id.in_(
                    select(GenotypeRecordModel.accession_id)
                    .where(GenotypeRecordModel.study_id == str(study_id))
                    .distinct()
                )
            )
            .order_by(AccessionModel.accession_name)
        ).all()
        if not sample_rows:
            raise RuntimeError(f"No accessions found for study {study_name} ({study_id})")
        sample_ids = [str(aid) for aid, _ in sample_rows]
        sample_names = [name for _, name in sample_rows]
        sample_idx = {aid: i for i, aid in enumerate(sample_ids)}
        n_samples = len(sample_ids)

        # 2. Variants — ordered by (chromosome, position) for Manhattan plot sanity.
        variant_rows = session.execute(
            select(
                VariantModel.id,
                VariantModel.variant_name,
                VariantModel.chromosome,
                VariantModel.position,
                VariantModel.alleles,
            )
            .where(
                VariantModel.id.in_(
                    select(GenotypeRecordModel.variant_id)
                    .where(GenotypeRecordModel.study_id == str(study_id))
                    .distinct()
                )
            )
            .order_by(VariantModel.chromosome, VariantModel.position)
        ).all()
        if not variant_rows:
            raise RuntimeError(f"No variants found for study {study_name} ({study_id})")
        variant_ids = [str(vid) for vid, _, _, _, _ in variant_rows]
        variant_idx = {vid: i for i, vid in enumerate(variant_ids)}
        n_variants = len(variant_ids)

        # A1/A2 per variant (A1 = alt, A2 = ref).
        a1_by_variant = []
        a2_by_variant = []
        variant_meta = []
        for vid, vname, chrom, pos_cm, alleles in variant_rows:
            ref, _, alt = (alleles or "N/N").partition("/")
            ref = ref.strip() or "0"
            alt = alt.strip() or "0"
            a1_by_variant.append(alt)
            a2_by_variant.append(ref)
            variant_meta.append({
                "variant_id": str(vid),
                "variant_name": vname,
                "chromosome": chrom,
                "position_cm": float(pos_cm) if pos_cm is not None else 0.0,
                "a1": alt,
                "a2": ref,
            })

        # 3. Allocate (n_variants, n_samples) genotype matrix, fill missing.
        matrix = np.full((n_variants, n_samples), CODE_MISSING, dtype=np.uint8)

        # 4. Stream genotype records, populate matrix.
        stmt = (
            select(
                GenotypeRecordModel.variant_id,
                GenotypeRecordModel.accession_id,
                GenotypeRecordModel.call_value,
            )
            .where(GenotypeRecordModel.study_id == str(study_id))
            .execution_options(yield_per=10_000)
        )
        for vid, aid, call in session.execute(stmt):
            vid_s = str(vid)
            aid_s = str(aid)
            i = variant_idx.get(vid_s)
            j = sample_idx.get(aid_s)
            if i is None or j is None:
                continue
            matrix[i, j] = _encode_call(call, a1_by_variant[i], a2_by_variant[i])

    # 5. Write .fam — FID=IID=accession_name, zeros for ped structure, -9 pheno.
    fam_path = out_dir / f"{basename}.fam"
    with fam_path.open("w") as f:
        for name in sample_names:
            # PLINK does not allow spaces in sample IDs; substitute underscores.
            safe = name.replace(" ", "_")
            f.write(f"{safe} {safe} 0 0 0 -9\n")

    # 6. Write .bim — chrom rs cM bp a1 a2.
    # PLINK2 rejects bp == 0 and requires bp to be non-decreasing within each
    # chromosome. GEMINI stores `Variant.position` as centiMorgans, so many
    # markers near a chromosome's origin legitimately have cM == 0 and would
    # all collide on bp == 0. Per chromosome, start with `max(1, cm*1e6)` and
    # bump to prev+1 whenever the scaled value would repeat or go backwards.
    bim_path = out_dir / f"{basename}.bim"
    last_bp_by_chrom: dict[int, int] = {}
    with bim_path.open("w") as f:
        for meta in variant_meta:
            chrom = meta["chromosome"]
            cm = meta["position_cm"]
            scaled = max(1, int(round(cm * 1_000_000)))
            prev = last_bp_by_chrom.get(chrom, 0)
            bp = scaled if scaled > prev else prev + 1
            last_bp_by_chrom[chrom] = bp
            f.write(
                f"{chrom} {meta['variant_name']} {cm} {bp} "
                f"{meta['a1']} {meta['a2']}\n"
            )

    # 7. Write .bed — magic header + bit-packed variant rows.
    bed_path = out_dir / f"{basename}.bed"
    with bed_path.open("wb") as f:
        f.write(bytes([0x6C, 0x1B, 0x01]))
        for i in range(n_variants):
            f.write(_pack_variant_row(matrix[i]))

    return PlinkPaths(
        bed=bed_path,
        bim=bim_path,
        fam=fam_path,
        samples=sample_names,
        variants=variant_meta,
    )


_AGGREGATORS = {
    "mean": lambda xs: mean(xs),
    "median": lambda xs: median(xs),
    "first": lambda xs: xs[0],
}


def write_phenotype(
    sample_order: list[str],
    trait_ids: Iterable[UUID | str],
    out_dir: Path,
    basename: str = "pheno",
    dataset_id: Optional[UUID | str] = None,
    experiment_id: Optional[UUID | str] = None,
    season_id: Optional[UUID | str] = None,
    site_id: Optional[UUID | str] = None,
    agg: str = "mean",
) -> tuple[Path, int]:
    """Write a .pheno file with one row per sample in sample_order.

    One column per trait_id (single-column for LMM, multi-column for mvLMM).
    Missing values emitted as -9 per GEMMA convention.

    Returns (path, n_samples_with_any_value).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if agg not in _AGGREGATORS:
        raise ValueError(f"Unknown phenotype_agg={agg!r}; expected one of {list(_AGGREGATORS)}")
    aggregator = _AGGREGATORS[agg]

    trait_ids = [str(t) for t in trait_ids]
    if not trait_ids:
        raise ValueError("write_phenotype requires at least one trait_id")

    # accession_name -> {trait_id -> [values...]}
    per_sample: dict[str, dict[str, list[float]]] = {name: {} for name in sample_order}

    with db_engine.get_session() as session:
        for trait_id in trait_ids:
            stmt = (
                select(
                    PlotAccessionViewModel.accession_name,
                    TraitRecordsIMMVModel.trait_value,
                )
                .join(
                    PlotAccessionViewModel,
                    TraitRecordsIMMVModel.plot_id == PlotAccessionViewModel.plot_id,
                )
                .where(TraitRecordsIMMVModel.trait_id == trait_id)
            )
            if dataset_id:
                stmt = stmt.where(TraitRecordsIMMVModel.dataset_id == str(dataset_id))
            if experiment_id:
                stmt = stmt.where(TraitRecordsIMMVModel.experiment_id == str(experiment_id))
            if season_id:
                stmt = stmt.where(TraitRecordsIMMVModel.season_id == str(season_id))
            if site_id:
                stmt = stmt.where(TraitRecordsIMMVModel.site_id == str(site_id))

            for accession_name, value in session.execute(stmt):
                if value is None or accession_name not in per_sample:
                    continue
                per_sample[accession_name].setdefault(trait_id, []).append(float(value))

    n_covered = 0
    pheno_path = out_dir / f"{basename}.pheno"
    with pheno_path.open("w") as f:
        for name in sample_order:
            row_values = []
            has_any = False
            for trait_id in trait_ids:
                observations = per_sample[name].get(trait_id)
                if observations:
                    row_values.append(f"{aggregator(observations):.6g}")
                    has_any = True
                else:
                    row_values.append("-9")
            if has_any:
                n_covered += 1
            f.write(" ".join(row_values) + "\n")

    return pheno_path, n_covered
