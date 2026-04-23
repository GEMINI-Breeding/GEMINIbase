"""
GWAS worker.

Consumes RUN_GWAS jobs from the REST API queue. Each job extracts genotype
data (from the GenotypingStudy's GenotypeRecord rows) plus phenotype data
(from TraitRecords resolved through the plot→accession view), runs the
standard pipeline:

    raw geno → PLINK QC → PCA → GEMMA kinship → GEMMA LMM/mvLMM
    → Manhattan + QQ plots → MinIO upload → job.result

See /Users/bnbailey/.claude/plans/sleepy-imagining-flamingo.md for the plan
this worker implements.
"""
from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Set

from gemini.workers.base import BaseWorker
from gemini.workers.gwas import extract, gemma_runner, plink_runner, plots
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")


def _get_minio_client():
    from minio import Minio

    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
    )


def _upload(client, local_path: Path, object_name: str, content_type: str = "application/octet-stream") -> str:
    client.fput_object(STORAGE_BUCKET, object_name, str(local_path), content_type=content_type)
    return f"s3://{STORAGE_BUCKET}/{object_name}"


class GwasWorker(BaseWorker):
    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.RUN_GWAS}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        model = parameters.get("model", "lmm")
        lmm_test = parameters.get("lmm_test", "wald")
        qc_params = parameters.get("qc") or {}
        n_pcs = int(parameters.get("n_pcs", 3))
        phenotype_agg = parameters.get("phenotype_agg", "mean")
        study_id = parameters["study_id"]
        dataset_id = parameters.get("dataset_id")
        experiment_id = parameters.get("experiment_id")
        season_id = parameters.get("season_id")
        site_id = parameters.get("site_id")

        if model == "mvlmm":
            trait_ids = parameters.get("trait_ids") or []
            if len(trait_ids) < 2:
                raise ValueError("mvlmm requires at least 2 trait_ids")
        else:
            single = parameters.get("trait_id")
            if not single:
                raise ValueError(f"model={model} requires trait_id")
            trait_ids = [single]

        # 1. Resolve study name (for logging + filter call).
        from gemini.api.genotyping_study import GenotypingStudy  # lazy: heavy import
        study = GenotypingStudy.get_by_id(id=study_id)
        if study is None:
            raise ValueError(f"GenotypingStudy {study_id} not found")
        self.report_progress(job_id, 2.0, {"stage": "validate", "study_name": study.study_name})

        with tempfile.TemporaryDirectory(prefix=f"gwas-{job_id}-") as tmp:
            work = Path(tmp)

            # 2. Extract genotypes.
            self.report_progress(job_id, 5.0, {"stage": "extract_genotypes"})
            raw = extract.write_plink_fileset(
                study_id=study.id, study_name=study.study_name, out_dir=work, basename="raw",
            )
            self.report_progress(job_id, 18.0, {
                "stage": "extract_genotypes",
                "n_samples": len(raw.samples),
                "n_variants": len(raw.variants),
            })

            # 3. QC (on genotypes only; phenotype alignment happens after).
            self.report_progress(job_id, 22.0, {"stage": "qc"})
            qc_result = plink_runner.qc(
                in_prefix=work / "raw",
                out_prefix=work / "qc",
                maf=float(qc_params.get("maf", 0.05)),
                geno=float(qc_params.get("geno", 0.1)),
                mind=float(qc_params.get("mind", 0.1)),
                hwe=float(qc_params.get("hwe", 1e-6)),
            )
            self.report_progress(job_id, 34.0, {
                "stage": "qc",
                "n_variants_before": qc_result.n_variants_before,
                "n_variants_after": qc_result.n_variants_after,
                "n_samples_before": qc_result.n_samples_before,
                "n_samples_after": qc_result.n_samples_after,
            })

            qc_fam = work / "qc.fam"
            qc_sanitized_order = [line.split()[1] for line in qc_fam.read_text().splitlines() if line.strip()]
            if not qc_sanitized_order:
                raise RuntimeError("QC dropped all samples")

            # .fam sanitizes spaces → underscores. Map each surviving IID back to
            # the DB accession_name so the phenotype join finds the right rows.
            sanitized_to_db = {name.replace(" ", "_"): name for name in raw.samples}
            qc_sample_order_db = [sanitized_to_db.get(iid, iid) for iid in qc_sanitized_order]

            # 4. Extract phenotype aligned to QC'd sample order.
            self.report_progress(job_id, 36.0, {"stage": "extract_phenotype"})
            pheno_path, n_covered = extract.write_phenotype(
                sample_order=qc_sample_order_db,
                trait_ids=trait_ids,
                out_dir=work,
                basename="pheno",
                dataset_id=dataset_id,
                experiment_id=experiment_id,
                season_id=season_id,
                site_id=site_id,
                agg=phenotype_agg,
            )
            if n_covered == 0:
                raise RuntimeError(
                    "No samples with both genotype and phenotype observations; "
                    "check that trait_id(s), dataset_id, and experiment_id match "
                    "accessions in the genotyping study."
                )

            # 5. PCA (or just write intercept-only covariate file).
            self.report_progress(job_id, 40.0, {"stage": "pca", "n_pcs": n_pcs})
            eigenvec_path = None
            if n_pcs > 0:
                eigenvec_path = plink_runner.pca(
                    in_prefix=work / "qc",
                    out_prefix=work / "pca",
                    n_pcs=max(n_pcs, 10),
                )
            plink_runner.write_gemma_covar(
                eigenvec_path=eigenvec_path or (work / "pca.eigenvec"),
                fam_path=qc_fam,
                covar_out=work / "covar.txt",
                n_pcs=n_pcs,
            )

            # 6. Kinship.
            self.report_progress(job_id, 48.0, {"stage": "kinship"})
            kin_path = gemma_runner.kinship(
                bed_prefix=work / "qc",
                work_dir=work,
                out_name="kin",
                kinship_type=1,
                pheno_path=pheno_path,
            )

            # 7. Association.
            self.report_progress(job_id, 58.0, {"stage": "association", "model": model})
            if model == "bslmm":
                run_result = gemma_runner.bslmm(
                    bed_prefix=work / "qc",
                    pheno_path=pheno_path,
                    work_dir=work,
                    out_name="run",
                )
            else:
                trait_columns = list(range(1, len(trait_ids) + 1)) if len(trait_ids) > 1 else None
                run_result = gemma_runner.lmm(
                    bed_prefix=work / "qc",
                    pheno_path=pheno_path,
                    kinship_path=kin_path,
                    covar_path=work / "covar.txt",
                    work_dir=work,
                    out_name="run",
                    test=lmm_test,
                    trait_columns=trait_columns,
                )

            # 8. Parse + plot (skipped for BSLMM — different output shape).
            client = _get_minio_client()
            prefix = f"gwas/{job_id}"
            artifacts: dict[str, str] = {}
            summary_payload: dict[str, Any] = {}

            if model != "bslmm":
                self.report_progress(job_id, 86.0, {"stage": "plot"})
                df, p_col = plots.load_assoc(run_result.assoc_path)
                assoc_summary = plots.summarize(df, p_col)

                manhattan_path = work / "manhattan.png"
                qq_path = work / "qq.png"
                plots.manhattan_plot(
                    df, p_col, manhattan_path,
                    title=f"GWAS — {study.study_name}",
                    bonferroni=assoc_summary.bonferroni_threshold,
                )
                plots.qq_plot(df, p_col, qq_path, title=f"QQ — {study.study_name}")

                artifacts["manhattan"] = _upload(client, manhattan_path, f"{prefix}/manhattan.png", "image/png")
                artifacts["qq"] = _upload(client, qq_path, f"{prefix}/qq.png", "image/png")
                summary_payload = {
                    "p_column": assoc_summary.p_column,
                    "genomic_inflation_lambda": assoc_summary.genomic_inflation_lambda,
                    "n_genome_wide_sig": assoc_summary.n_genome_wide,
                    "n_suggestive": assoc_summary.n_suggestive,
                    "bonferroni_threshold": assoc_summary.bonferroni_threshold,
                    "n_bonferroni_sig": assoc_summary.n_bonferroni,
                    "top_hits": assoc_summary.top_hits,
                }

            # 9. Upload core artifacts.
            self.report_progress(job_id, 94.0, {"stage": "upload"})
            artifacts["assoc"] = _upload(client, run_result.assoc_path, f"{prefix}/{run_result.assoc_path.name}", "text/plain")
            if run_result.log_path.exists():
                artifacts["gemma_log"] = _upload(client, run_result.log_path, f"{prefix}/{run_result.log_path.name}", "text/plain")
            artifacts["kinship"] = _upload(client, kin_path, f"{prefix}/{kin_path.name}", "text/plain")
            if qc_result.log_path.exists():
                artifacts["qc_log"] = _upload(client, qc_result.log_path, f"{prefix}/qc.log", "text/plain")
            if eigenvec_path and eigenvec_path.exists():
                artifacts["pca_eigenvec"] = _upload(client, eigenvec_path, f"{prefix}/pca.eigenvec", "text/plain")
            covar_path = work / "covar.txt"
            if covar_path.exists():
                artifacts["covar"] = _upload(client, covar_path, f"{prefix}/covar.txt", "text/plain")
            for suffix in ("bed", "bim", "fam"):
                p = work / f"qc.{suffix}"
                if p.exists():
                    artifacts[f"qc_{suffix}"] = _upload(client, p, f"{prefix}/qc.{suffix}")

            result = {
                "artifacts": artifacts,
                "study_id": str(study.id),
                "study_name": study.study_name,
                "trait_ids": [str(t) for t in trait_ids],
                "model": model,
                "lmm_test": lmm_test if model == "lmm" else None,
                "n_pcs_used": n_pcs,
                "n_variants_input": qc_result.n_variants_before,
                "n_variants_passed_qc": qc_result.n_variants_after,
                "n_samples_input": qc_result.n_samples_before,
                "n_samples_passed_qc": qc_result.n_samples_after,
                "n_samples_with_phenotype": n_covered,
                **summary_payload,
            }

            # 10. Drop a JSON copy of the full result into MinIO for easy retrieval.
            result_buf = io.BytesIO(json.dumps(result, indent=2, default=str).encode())
            client.put_object(
                STORAGE_BUCKET,
                f"{prefix}/result.json",
                result_buf,
                length=result_buf.getbuffer().nbytes,
                content_type="application/json",
            )
            artifacts["result_json"] = f"s3://{STORAGE_BUCKET}/{prefix}/result.json"
            result["artifacts"] = artifacts

            return result


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("GEMINI_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    GwasWorker().run()
