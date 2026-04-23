"""
GWAS submission controller.

Thin layer over Job.create that validates GWAS-specific inputs and fans out
N independent jobs when the caller submits a list of traits with a univariate
model. Real work happens in the gwas worker (gemini/workers/gwas/worker.py).
"""
from typing import Annotated, List

from litestar import Response
from litestar.controller import Controller
from litestar.handlers import post
from litestar.params import Body

from gemini.api.job import Job
from gemini.rest_api.models import (
    GwasSubmitInput,
    JobOutput,
    RESTAPIError,
)

_VALID_MODELS = {"lmm", "mvlmm", "bslmm"}
_VALID_LMM_TESTS = {"wald", "lrt", "score", "all"}
_VALID_AGG = {"mean", "median", "first"}


class GwasController(Controller):

    @post(path="/submit", sync_to_thread=True)
    def submit_gwas(self, data: Annotated[GwasSubmitInput, Body]) -> List[JobOutput]:
        """Submit one or more RUN_GWAS jobs.

        - `model="lmm"` or `"bslmm"` + `trait_id`: 1 job.
        - `model="lmm"` or `"bslmm"` + `trait_ids`: N jobs (one per trait).
        - `model="mvlmm"` + `trait_ids` (len ≥ 2): 1 multivariate job.

        Returns the list of created JobOutputs.
        """
        if data.model not in _VALID_MODELS:
            return Response(
                content=RESTAPIError(
                    error="Invalid model",
                    error_description=f"model must be one of {sorted(_VALID_MODELS)}",
                ),
                status_code=400,
            )
        if data.lmm_test not in _VALID_LMM_TESTS:
            return Response(
                content=RESTAPIError(
                    error="Invalid lmm_test",
                    error_description=f"lmm_test must be one of {sorted(_VALID_LMM_TESTS)}",
                ),
                status_code=400,
            )
        if data.phenotype_agg not in _VALID_AGG:
            return Response(
                content=RESTAPIError(
                    error="Invalid phenotype_agg",
                    error_description=f"phenotype_agg must be one of {sorted(_VALID_AGG)}",
                ),
                status_code=400,
            )
        if data.n_pcs < 0 or data.n_pcs > 20:
            return Response(
                content=RESTAPIError(
                    error="Invalid n_pcs",
                    error_description="n_pcs must be between 0 and 20",
                ),
                status_code=400,
            )

        trait_ids = data.trait_ids or ([data.trait_id] if data.trait_id else [])
        trait_ids = [str(t) for t in trait_ids if t is not None]
        if not trait_ids:
            return Response(
                content=RESTAPIError(
                    error="No trait specified",
                    error_description="Provide either trait_id or trait_ids",
                ),
                status_code=400,
            )

        if data.model == "mvlmm":
            if len(trait_ids) < 2:
                return Response(
                    content=RESTAPIError(
                        error="mvlmm requires multiple traits",
                        error_description="Provide trait_ids with at least 2 entries for mvLMM",
                    ),
                    status_code=400,
                )
            runs = [{"mvlmm": True, "trait_ids": trait_ids}]
        else:
            runs = [{"mvlmm": False, "trait_ids": [tid]} for tid in trait_ids]

        common = {
            "study_id": str(data.study_id),
            "experiment_id": str(data.experiment_id),
            "dataset_id": str(data.dataset_id),
            "season_id": str(data.season_id) if data.season_id else None,
            "site_id": str(data.site_id) if data.site_id else None,
            "model": data.model,
            "lmm_test": data.lmm_test,
            "n_pcs": data.n_pcs,
            "phenotype_agg": data.phenotype_agg,
            "qc": data.qc or {},
        }

        jobs: List[JobOutput] = []
        for run in runs:
            params = dict(common)
            if run["mvlmm"]:
                params["trait_ids"] = run["trait_ids"]
            else:
                params["trait_id"] = run["trait_ids"][0]
            job = Job.create(
                job_type="RUN_GWAS",
                parameters=params,
                experiment_id=data.experiment_id,
            )
            if job is None:
                return Response(
                    content=RESTAPIError(
                        error="Job creation failed",
                        error_description="Job.create returned None",
                    ),
                    status_code=500,
                )
            jobs.append(job)

        return jobs
