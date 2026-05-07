"""
Extract genotype + phenotype data from MinIO PGEN + Postgres metadata, and
write PLINK1-format binary filesets (.bed/.bim/.fam) plus a .pheno file for
GEMMA.

The .bed/.bim/.fam trio is produced by ``plink2 --pfile … --make-bed`` from
the canonical PGEN trio uploaded at ingest time; we don't bit-pack rows in
Python anymore.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select

from gemini.db.core.base import db_engine
from gemini.db.models.accessions import AccessionModel
from gemini.db.models.variants import VariantModel
from gemini.db.models.views.plot_accession_view import PlotAccessionViewModel
from gemini.db.models.views.trait_records_immv import TraitRecordsIMMVModel


@dataclass(frozen=True)
class PlinkPaths:
    bed: Path
    bim: Path
    fam: Path
    samples: list[str]   # accession_name order used in .fam
    variants: list[dict]  # variant metadata in .bim row order


def write_plink_fileset(
    study_id: UUID | str,
    study_name: str,
    out_dir: Path,
    basename: str = "geno",
) -> PlinkPaths:
    """Phase 9d': pull the study's PGEN trio out of MinIO and convert to
    PLINK1 BED via ``plink2 --make-bed``.

    Replaces the legacy implementation that streamed every
    (variant, accession, call) row from a Hydra columnar tall table and
    bit-packed a numpy matrix in Python. PGEN already encodes the same
    biallelic genotypes; PLINK2 reads it natively and emits BED+BIM+FAM
    in a single pass with zero Python intermediate.

    The returned ``PlinkPaths`` keeps the legacy shape so the GWAS
    worker's downstream code (GEMMA invocation, variant_meta lookup
    for the artefact loader) doesn't need to change.
    """
    import shutil
    import subprocess

    from gemini.api.base import minio_storage_provider
    from gemini.db.models.genotyping_study_files import (
        GenotypingStudyFileModel,
    )
    from gemini.db.models.genotyping_study_samples import (
        GenotypingStudySampleModel,
    )
    from gemini.db.models.genotyping_study_variants import (
        GenotypingStudyVariantModel,
    )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch file pointers + sample/variant catalogs.
    with db_engine.get_session() as session:
        files = {
            row.file_kind: row.s3_uri
            for row in session.execute(
                select(GenotypingStudyFileModel).where(
                    GenotypingStudyFileModel.study_id == str(study_id)
                )
            ).scalars()
        }
        sample_rows = session.execute(
            select(
                AccessionModel.accession_name,
                GenotypingStudySampleModel.sample_index,
            )
            .join(
                GenotypingStudySampleModel,
                GenotypingStudySampleModel.accession_id == AccessionModel.id,
            )
            .where(GenotypingStudySampleModel.study_id == str(study_id))
            .order_by(GenotypingStudySampleModel.sample_index)
        ).all()
        variant_rows = session.execute(
            select(
                VariantModel.id,
                VariantModel.variant_name,
                VariantModel.chromosome,
                VariantModel.position,
                VariantModel.alleles,
                GenotypingStudyVariantModel.variant_index,
            )
            .join(
                GenotypingStudyVariantModel,
                GenotypingStudyVariantModel.variant_id == VariantModel.id,
            )
            .where(GenotypingStudyVariantModel.study_id == str(study_id))
            .order_by(GenotypingStudyVariantModel.variant_index)
        ).all()

    if not files:
        raise RuntimeError(
            f"Study {study_name} ({study_id}) has no MinIO file pointers; "
            f"was it ingested via the legacy path? Re-import via /files."
        )
    if not sample_rows:
        raise RuntimeError(
            f"No samples found for study {study_name} ({study_id})"
        )
    if not variant_rows:
        raise RuntimeError(
            f"No variants found for study {study_name} ({study_id})"
        )

    sample_names = [name for name, _ in sample_rows]
    variant_meta = []
    for vid, vname, chrom, pos_cm, alleles, _idx in variant_rows:
        ref, _, alt = (alleles or "N/N").partition("/")
        variant_meta.append({
            "variant_id": str(vid),
            "variant_name": vname,
            "chromosome": chrom,
            "position_cm": float(pos_cm) if pos_cm is not None else 0.0,
            "a1": alt.strip() or "0",
            "a2": ref.strip() or "0",
        })

    # 2. Download the PGEN trio from MinIO into out_dir under the input
    #    prefix `geno_in.*`. plink2 needs all three siblings present.
    in_prefix = out_dir / "geno_in"
    for kind in ("pgen", "pvar", "psam"):
        uri = files.get(kind)
        if not uri:
            raise RuntimeError(
                f"Study {study_name} is missing its .{kind} file pointer."
            )
        bucket, _, object_name = uri.removeprefix("s3://").partition("/")
        local = in_prefix.with_suffix(f".{kind}")
        minio_storage_provider.client.fget_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=str(local),
        )

    # 3. plink2 --pfile … --make-bed --out <basename>.
    out_prefix = out_dir / basename
    cmd = [
        "plink2",
        "--pfile", str(in_prefix),
        "--make-bed",
        "--out", str(out_prefix),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"plink2 --make-bed failed (exit {res.returncode}): "
            f"{res.stderr[:1000]}"
        )

    bed_path = out_prefix.with_suffix(".bed")
    bim_path = out_prefix.with_suffix(".bim")
    fam_path = out_prefix.with_suffix(".fam")
    if not (bed_path.exists() and bim_path.exists() and fam_path.exists()):
        raise RuntimeError(
            f"plink2 --make-bed produced incomplete output in {out_dir}"
        )

    # 4. Clean up the intermediate input copies; they're not needed
    #    downstream and would double the worker's disk footprint.
    for kind in ("pgen", "pvar", "psam"):
        try:
            in_prefix.with_suffix(f".{kind}").unlink()
        except FileNotFoundError:
            pass

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
