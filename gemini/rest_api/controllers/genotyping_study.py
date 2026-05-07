import json
import tempfile
from pathlib import Path

from litestar import Response
from litestar.enums import RequestEncodingType
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.genotyping_study import GenotypingStudy
from gemini.api.genotyping_pgen_ingest import ingest_genotype_file
from gemini.api.variant import Variant
from gemini.api.accession import Accession
from gemini.db.models.variants import VariantModel
from gemini.db.models.accessions import AccessionModel
from gemini.db.core.base import db_engine
from gemini.rest_api.models import (
    GenotypingStudyInput,
    GenotypingStudyOutput,
    GenotypingStudyUpdate,
    GenotypeRecordOutput,
    GenotypePgenIngestRequest,
    GenotypePgenIngestResult,
    ExperimentOutput,
    RESTAPIError,
    str_to_dict,
    JSONB,
)

from typing import List, Annotated, Optional


class GenotypingStudyController(Controller):

    @get(path="/all", sync_to_thread=True)
    def get_all_studies(self, limit: int = 100, offset: int = 0) -> List[GenotypingStudyOutput]:
        try:
            studies = GenotypingStudy.get_all(limit=limit, offset=offset)
            return studies or []
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(sync_to_thread=True)
    def search_studies(
        self,
        study_name: Optional[str] = None,
        study_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = None,
    ) -> List[GenotypingStudyOutput]:
        try:
            if study_info is not None:
                study_info = str_to_dict(study_info)
            return GenotypingStudy.search(study_name=study_name, study_info=study_info, experiment_name=experiment_name) or []
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{study_id:str}", sync_to_thread=True)
    def get_study_by_id(self, study_id: str) -> GenotypingStudyOutput:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Genotyping study not found", error_description=""), status_code=404)
            return study
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @post(sync_to_thread=True)
    def create_study(self, data: Annotated[GenotypingStudyInput, Body]) -> GenotypingStudyOutput:
        try:
            study = GenotypingStudy.create(
                study_name=data.study_name,
                study_info=data.study_info,
                experiment_name=data.experiment_name,
            )
            if study is None:
                return Response(content=RESTAPIError(error="Creation failed", error_description=""), status_code=500)
            return study
        except ValueError as e:
            # Bad-request shape: e.g. a non-existent experiment_name.
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=400)
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @patch(path="/id/{study_id:str}", sync_to_thread=True)
    def update_study(self, study_id: str, data: Annotated[GenotypingStudyUpdate, Body]) -> GenotypingStudyOutput:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            study = study.update(study_name=data.study_name, study_info=data.study_info)
            if study is None:
                return Response(content=RESTAPIError(error="Update failed", error_description=""), status_code=500)
            return study
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @delete(path="/id/{study_id:str}", sync_to_thread=True)
    def delete_study(self, study_id: str) -> None:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description="").to_html(), status_code=404)
            if not study.delete():
                return Response(content=RESTAPIError(error="Deletion failed", error_description=""), status_code=500)
            return None
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{study_id:str}/experiments", sync_to_thread=True)
    def get_associated_experiments(self, study_id: str) -> List[ExperimentOutput]:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            return study.get_associated_experiments() or []
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @post(
        path="/id/{study_id:str}/ingest-pgen",
        sync_to_thread=True,
    )
    def ingest_pgen(
        self,
        study_id: str,
        data: Annotated[
            GenotypePgenIngestRequest,
            Body(media_type=RequestEncodingType.MULTI_PART),
        ],
    ) -> GenotypePgenIngestResult:
        """Phase 9d' replacement for ``ingest-matrix``.

        Accepts a single multipart file (xlsx/HapMap/VCF/CSV/TSV) plus
        the wizard's resolution metadata. Server-side: transcodes to a
        normalised VCF, runs ``plink2 --make-pgen`` to produce the
        canonical PGEN trio + BCF + per-variant stats CSV, uploads
        everything to MinIO under ``genotyping/{study_id}/``, and
        records pointers + variant/sample catalogs in Postgres.
        """
        import logging, traceback

        try:
            sample_canonical_map = (
                json.loads(data.sample_canonical_map_json)
                if data.sample_canonical_map_json
                else {}
            )
            skipped_headers = (
                json.loads(data.skipped_headers_json)
                if data.skipped_headers_json
                else []
            )
            created_accessions = (
                json.loads(data.created_accessions_json)
                if data.created_accessions_json
                else []
            )
            # Save the upload to a temp file so plink2/bcftools can
            # access it on disk. The TemporaryDirectory inside the
            # ingest helper handles per-study scratch space; this one
            # only has to survive the duration of this handler.
            filename = data.file.filename or "upload.bin"
            with tempfile.NamedTemporaryFile(
                suffix="-" + filename,
                delete=False,
            ) as tmp:
                # data.file is a Litestar UploadFile (an aiofiles
                # SpooledTemporaryFile); read in 4 MiB chunks so big
                # uploads don't materialise in memory.
                while True:
                    chunk = data.file.file.read(4 << 20)
                    if not chunk:
                        break
                    tmp.write(chunk)
                tmp_path = Path(tmp.name)
            try:
                result = ingest_genotype_file(
                    study_id=study_id,
                    upload_path=tmp_path,
                    upload_filename=filename,
                    sample_canonical_map=sample_canonical_map,
                    skipped_headers=skipped_headers,
                    created_accessions=created_accessions,
                    experiment_name=data.experiment_name,
                    population_name=data.population_name,
                )
            finally:
                tmp_path.unlink(missing_ok=True)

            return GenotypePgenIngestResult(
                variants_inserted=result.variants_inserted,
                records_inserted=result.records_inserted,
                samples_inserted=result.samples_inserted,
                files=result.files,
                errors=result.errors,
            )
        except Exception as e:
            logging.getLogger(__name__).error(
                "ingest_pgen failed: %s\n%s", e, traceback.format_exc(),
            )
            return Response(
                content=RESTAPIError(error=str(e), error_description=""),
                status_code=500,
            )

    @get(path="/id/{study_id:str}/records", sync_to_thread=True)
    def get_records(
        self,
        study_id: str,
        variant_name: Optional[str] = None,
        accession_name: Optional[str] = None,
        chromosome: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GenotypeRecordOutput]:
        """Paginated (variant × sample × call) listing.

        Genotype calls live in PGEN files in MinIO; we crack the BCF
        sibling on demand via ``bcftools query`` and synthesise the
        per-call rows for this page. Millisecond per-call lookups are
        not a requirement (only batched analytics + export), so this
        endpoint deliberately runs ``bcftools`` per page rather than
        maintaining a hot index. The variant browser (Phase 9f) reads
        ``genotyping_study_variants`` directly for catalog views.
        """
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path

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
        from sqlalchemy import select

        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(
                    content=RESTAPIError(error="Not found", error_description=""),
                    status_code=404,
                )

            limit = max(1, min(limit, 500))
            offset = max(0, offset)

            # 1. Resolve sample list (sample_index → accession_name) and
            #    page over variants via the catalog. One variant_row →
            #    n_samples records, so we figure out which variant_index
            #    range covers (offset, offset+limit) calls.
            with db_engine.get_session() as session:
                files = {
                    row.file_kind: row.s3_uri
                    for row in session.execute(
                        select(GenotypingStudyFileModel).where(
                            GenotypingStudyFileModel.study_id == str(study.id)
                        )
                    ).scalars()
                }
                if "bcf" not in files:
                    # Empty result set is the right answer for studies
                    # that haven't been ingested yet (e.g. just-created).
                    return []
                sample_list = [
                    (idx, name)
                    for name, idx in session.execute(
                        select(
                            AccessionModel.accession_name,
                            GenotypingStudySampleModel.sample_index,
                        )
                        .join(
                            GenotypingStudySampleModel,
                            GenotypingStudySampleModel.accession_id
                            == AccessionModel.id,
                        )
                        .where(
                            GenotypingStudySampleModel.study_id == str(study.id)
                        )
                        .order_by(GenotypingStudySampleModel.sample_index)
                    ).all()
                ]
                if accession_name:
                    sample_list = [
                        (i, n) for i, n in sample_list if n == accession_name
                    ]
                if not sample_list:
                    return []
                n_samples = len(sample_list)

                # Variant catalog (filter by name/chrom if requested).
                vq = (
                    select(
                        VariantModel.id,
                        VariantModel.variant_name,
                        VariantModel.chromosome,
                        VariantModel.position,
                        VariantModel.alleles,
                    )
                    .join(
                        GenotypingStudyVariantModel,
                        GenotypingStudyVariantModel.variant_id == VariantModel.id,
                    )
                    .where(GenotypingStudyVariantModel.study_id == str(study.id))
                    .order_by(GenotypingStudyVariantModel.variant_index)
                )
                if variant_name:
                    vq = vq.where(VariantModel.variant_name == variant_name)
                if chromosome is not None:
                    vq = vq.where(VariantModel.chromosome == chromosome)
                variants = list(session.execute(vq).all())
            if not variants:
                return []

            # 2. Map flat (offset, limit) into (variant_start, sample_start)
            #    → variant_end (exclusive).
            start = offset
            end = offset + limit
            # Total rows under filter = n_samples × len(variants).
            # We crack only the variant slice that overlaps [start, end).
            v_start = start // n_samples
            v_end = min(len(variants), (end + n_samples - 1) // n_samples)
            if v_start >= len(variants):
                return []
            slice_variants = variants[v_start:v_end]

            # 3. Download the BCF + index from MinIO and run
            #    ``bcftools query`` for the variant IDs we want.
            with tempfile.TemporaryDirectory(
                prefix=f"gemini-records-{study.id}-",
            ) as tmp:
                work = Path(tmp)
                bcf_uri = files["bcf"]
                bucket, _, object_name = bcf_uri.removeprefix("s3://").partition("/")
                local_bcf = work / "geno.bcf"
                minio_storage_provider.client.fget_object(
                    bucket_name=bucket,
                    object_name=object_name,
                    file_path=str(local_bcf),
                )
                idx_uri = files.get("bcf_index")
                if idx_uri:
                    bucket_i, _, obj_i = idx_uri.removeprefix("s3://").partition("/")
                    minio_storage_provider.client.fget_object(
                        bucket_name=bucket_i,
                        object_name=obj_i,
                        file_path=str(local_bcf) + ".csi",
                    )
                else:
                    # No CSI shipped — generate one in place. Cheap.
                    subprocess.run(
                        ["bcftools", "index", "--csi", str(local_bcf)],
                        capture_output=True, text=True, check=True,
                    )

                # bcftools query --include 'ID=@names.txt' streams only the
                # rows we want. Output: ID\tCHROM\tPOS\t[GT1,GT2,…]
                names_file = work / "ids.txt"
                with names_file.open("w") as fh:
                    for _, vname, _, _, _ in slice_variants:
                        fh.write(vname + "\n")
                cmd = [
                    "bcftools", "query",
                    "-i", f"ID=@{names_file}",
                    "-f", "%ID\\t%CHROM\\t%POS\\t%REF\\t%ALT\\t[%GT,]\\n",
                    str(local_bcf),
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(
                        f"bcftools query failed: {res.stderr[:500]}"
                    )

            # 4. Parse query output and synthesise GenotypeRecordOutputs.
            calls_by_variant: dict[str, dict[str, str]] = {}
            for line in res.stdout.splitlines():
                cols = line.rstrip("\n").split("\t")
                if len(cols) < 6:
                    continue
                vid_name, chrom_s, pos_s, ref, alt, gt_blob = (
                    cols[0], cols[1], cols[2], cols[3], cols[4], cols[5]
                )
                gts = [g for g in gt_blob.rstrip(",").split(",") if g]
                # Translate VCF GT (e.g. "0/1") back to a 2-letter call.
                per_sample: dict[str, str] = {}
                for (sidx, sname), gt in zip(sample_list, gts):
                    per_sample[sname] = _gt_to_call(gt, ref, alt)
                calls_by_variant[vid_name] = per_sample

            # 5. Project onto the flat (variant, sample, call) tuples,
            #    skipping the leading sample-rows of the first variant
            #    that fall before `start`.
            out: list[GenotypeRecordOutput] = []
            cursor = v_start * n_samples
            for vid, vname, chrom, pos, alleles in slice_variants:
                samples_for_v = calls_by_variant.get(vname, {})
                for sidx, sname in sample_list:
                    if cursor < start:
                        cursor += 1
                        continue
                    if cursor >= end:
                        break
                    out.append(
                        GenotypeRecordOutput(
                            id=None,
                            study_id=study.id,
                            study_name=study.study_name,
                            variant_id=vid,
                            variant_name=vname,
                            chromosome=chrom,
                            position=pos,
                            accession_id=None,
                            accession_name=sname,
                            call_value=samples_for_v.get(sname, "NN"),
                            record_info={},
                        )
                    )
                    cursor += 1
                if cursor >= end:
                    break
            return out
        except Exception as e:
            import logging, traceback
            logging.getLogger(__name__).error(
                "get_records failed: %s\n%s", e, traceback.format_exc(),
            )
            return Response(
                content=RESTAPIError(error=str(e), error_description=""),
                status_code=500,
            )

    @get(path="/id/{study_id:str}/export", sync_to_thread=True)
    def export_study(self, study_id: str, format: str = "hapmap", coding: str = "012") -> Response:
        try:
            study = GenotypingStudy.get_by_id(id=study_id)
            if study is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            content = study.export(format=format, coding=coding)
            if not content:
                return Response(content=RESTAPIError(error="No data to export", error_description=""), status_code=404)
            ext_map = {"hapmap": ".hmp.txt", "vcf": ".vcf", "numeric": ".num.txt", "plink": ".ped"}
            mime_map = {"hapmap": "text/tab-separated-values", "vcf": "text/plain", "numeric": "text/tab-separated-values", "plink": "text/plain"}
            ext = ext_map.get(format, ".txt")
            mime = mime_map.get(format, "text/plain")
            filename = f"{study.study_name}{ext}"
            return Response(content=content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
        except ValueError as e:
            return Response(content=RESTAPIError(error=str(e), error_description="Invalid export format"), status_code=400)
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)


def _gt_to_call(gt: str, ref: str, alt: str) -> str:
    """Translate a VCF GT field (``0/0``, ``0/1``, ``1/1``, ``./.``) to
    a 2-letter call (``"AA"``, ``"AG"``, ``"GG"``, ``"NN"``). Used by the
    PGEN-backed ``get_records`` endpoint."""
    if not gt or gt in (".", "./.", ".|."):
        return "NN"
    sep = "|" if "|" in gt else "/"
    parts = gt.split(sep)
    if len(parts) != 2:
        return "NN"
    a = ref if parts[0] == "0" else alt if parts[0] == "1" else "N"
    b = ref if parts[1] == "0" else alt if parts[1] == "1" else "N"
    return f"{a[:1]}{b[:1]}"
