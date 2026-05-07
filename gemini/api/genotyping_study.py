"""
This module defines the GenotypingStudy class, which represents a genotyping
study/protocol in the Gemini API.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.genotyping_studies import GenotypingStudyModel
from gemini.db.models.associations import ExperimentGenotypingStudyModel
from gemini.db.models.views.genotype_views import ExperimentGenotypingStudiesViewModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment

logger = logging.getLogger(__name__)


class GenotypingStudy(APIBase):

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "study_id"))

    study_name: str
    study_info: Optional[dict] = None

    def __str__(self):
        return f"GenotypingStudy(study_name={self.study_name}, id={self.id})"

    def __repr__(self):
        return f"GenotypingStudy(study_name={self.study_name}, id={self.id})"

    @classmethod
    def exists(cls, study_name: str) -> bool:
        try:
            return GenotypingStudyModel.exists(study_name=study_name)
        except Exception as e:
            logger.error(f"Error checking existence of genotyping study: {e}")
            return False

    @classmethod
    def create(
        cls,
        study_name: str,
        study_info: dict = None,
        experiment_name: str = None,
    ) -> Optional["GenotypingStudy"]:
        try:
            db_instance = GenotypingStudyModel.get_or_create(
                study_name=study_name,
                study_info=study_info,
            )
            study = cls.model_validate(db_instance)
            if experiment_name:
                associated = study.associate_experiment(experiment_name)
                if associated is None:
                    # Caller asked for an association but the named
                    # experiment doesn't exist. Don't silently leave
                    # the study orphaned — it's the bug that produced
                    # the "No experiments associated" detail-page hint.
                    raise ValueError(
                        f"Experiment '{experiment_name}' does not exist; "
                        f"create it before referencing it from a study."
                    )
            return study
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating genotyping study: {e}")
            return None

    @classmethod
    def get(cls, study_name: str, experiment_name: str = None) -> Optional["GenotypingStudy"]:
        try:
            if experiment_name:
                db_instance = ExperimentGenotypingStudiesViewModel.get_by_parameters(
                    study_name=study_name,
                    experiment_name=experiment_name,
                )
            else:
                db_instance = GenotypingStudyModel.get_by_parameters(study_name=study_name)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting genotyping study: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["GenotypingStudy"]:
        try:
            db_instance = GenotypingStudyModel.get(id)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting genotyping study by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["GenotypingStudy"]]:
        try:
            studies = GenotypingStudyModel.all(limit=limit, offset=offset)
            if not studies or len(studies) == 0:
                return None
            return [cls.model_validate(s) for s in studies]
        except Exception as e:
            logger.error(f"Error getting all genotyping studies: {e}")
            return None

    @classmethod
    def search(
        cls,
        study_name: str = None,
        study_info: dict = None,
        experiment_name: str = None,
    ) -> Optional[List["GenotypingStudy"]]:
        try:
            if not any([study_name, study_info, experiment_name]):
                logger.warning("At least one search parameter must be provided.")
                return None
            studies = ExperimentGenotypingStudiesViewModel.search(
                study_name=study_name,
                study_info=study_info,
                experiment_name=experiment_name,
            )
            if not studies or len(studies) == 0:
                return None
            return [cls.model_validate(s) for s in studies]
        except Exception as e:
            logger.error(f"Error searching genotyping studies: {e}")
            return None

    def update(self, study_name: str = None, study_info: dict = None) -> Optional["GenotypingStudy"]:
        try:
            if not any([study_name, study_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            db_instance = GenotypingStudyModel.get(self.id)
            if not db_instance:
                return None
            rename = study_name is not None and study_name != db_instance.study_name
            db_instance = GenotypingStudyModel.update(db_instance, study_name=study_name, study_info=study_info)
            if rename:
                from gemini.api._rename_cascade import cascade_rename
                cascade_rename(self.id, "study_id", "study_name", study_name)
            study = self.model_validate(db_instance)
            self.refresh()
            return study
        except Exception as e:
            logger.error(f"Error updating genotyping study: {e}")
            return None

    def delete(self) -> bool:
        """Delete the study row + sweep its MinIO artefacts.

        The schema has ON DELETE CASCADE on every per-study metadata
        table (``genotyping_study_files``, ``genotyping_study_variants``,
        ``genotyping_study_samples``, ``genotyping_study_variant_stats``),
        so removing the ``genotyping_studies`` row automatically reaps
        the catalog. Variants are a shared catalog handled by the
        orphan sweep below.

        MinIO is swept by **prefix** (``genotyping/{study_id}/``)
        rather than by file_pointer row, because re-ingest can leave
        orphan objects under the prefix whose row got overwritten:
        ``_upsert_files`` deletes-then-inserts the rows but doesn't
        prune the old MinIO objects, so e.g. an older source file's
        entry can be replaced while the object itself lingers. Sweep
        before the DB delete so a failure can be retried without
        losing the catalog.
        """
        try:
            from gemini.api.base import minio_storage_provider
            from gemini.db.core.base import db_engine
            from gemini.db.models.accessions import AccessionModel
            from gemini.db.models.genotyping_study_samples import (
                GenotypingStudySampleModel,
            )
            from gemini.db.models.plots import PlotModel
            from gemini.db.models.variants import VariantModel
            from sqlalchemy import select

            db_instance = GenotypingStudyModel.get(self.id)
            if not db_instance:
                return False

            # 1. Sweep every object under this study's MinIO prefix.
            #    Catches both currently-pointed-to artefacts and any
            #    orphans left by re-ingest. Prefix is the canonical
            #    layout written by `genotyping_pgen_ingest`.
            bucket = minio_storage_provider.bucket_name
            prefix = f"genotyping/{self.id}/"
            try:
                objs = list(minio_storage_provider.client.list_objects(
                    bucket_name=bucket, prefix=prefix, recursive=True,
                ))
            except Exception as exc:
                logger.warning(
                    "MinIO list_objects(%s) failed: %s", prefix, exc
                )
                objs = []
            for obj in objs:
                try:
                    minio_storage_provider.client.remove_object(
                        bucket_name=bucket, object_name=obj.object_name,
                    )
                except Exception as exc:
                    # A missing object isn't fatal for study deletion
                    # (hard-delete path; orphan files are an acceptable
                    # cost). Logged so an operator can pick them up.
                    logger.warning(
                        "MinIO remove_object %s failed: %s",
                        obj.object_name, exc,
                    )

            # 2. Sweep variants that this study was the sole reference
            #    for. The variants catalog is shared, so we only drop
            #    variants whose only remaining link was via this study
            #    (i.e. no remaining row in `genotyping_study_variants`).
            with db_engine.get_session() as session:
                from gemini.db.models.genotyping_study_variants import (
                    GenotypingStudyVariantModel,
                )
                # Variants in this study before we drop its catalog rows.
                variant_candidates = list(set(session.execute(
                    select(GenotypingStudyVariantModel.variant_id).where(
                        GenotypingStudyVariantModel.study_id == self.id
                    )
                ).scalars().all()))

                # Accessions in this study before the cascade drops the
                # `genotyping_study_samples` rows. We sweep orphans
                # post-delete: an accession is "wizard-created and
                # otherwise unused" iff after the cascade it has no
                # remaining `genotyping_study_samples` row in any other
                # study AND no `plots` row pointing at it. Without this
                # sweep, the wizard's first import creates ~300
                # accession rows; deleting the study leaves them in
                # `gemini.accessions`; the next import's sample-resolve
                # finds them by name and reports every sample as
                # already-resolved (the user-visible bug).
                accession_candidates = list(set(session.execute(
                    select(GenotypingStudySampleModel.accession_id).where(
                        GenotypingStudySampleModel.study_id == self.id
                    )
                ).scalars().all()))

            # 3. Delete the study. CASCADE removes file pointers,
            #    study_variants, study_samples, study_variant_stats.
            GenotypingStudyModel.delete(db_instance)

            # 4. Now sweep orphan variants (those that no other study
            #    references via study_variants).
            if variant_candidates:
                with db_engine.get_session() as session:
                    from gemini.db.models.genotyping_study_variants import (
                        GenotypingStudyVariantModel,
                    )
                    still_ref = set(session.execute(
                        select(GenotypingStudyVariantModel.variant_id).where(
                            GenotypingStudyVariantModel.variant_id.in_(
                                variant_candidates
                            )
                        ).distinct()
                    ).scalars().all())
                    orphan = [
                        v for v in variant_candidates if v not in still_ref
                    ]
                    if orphan:
                        session.execute(
                            VariantModel.__table__.delete().where(
                                VariantModel.id.in_(orphan)
                            )
                        )
                        session.commit()
                        logger.info(
                            "Deleted %d orphan variant(s) after deleting "
                            "study %s.", len(orphan), self.study_name,
                        )

            # 5. Sweep orphan accessions: any accession this study
            #    referenced that now has no remaining links from
            #    `genotyping_study_samples` (other studies) or `plots`
            #    (the trait wizard's plot rows). `accession_aliases`
            #    rows CASCADE-delete with their parent accession, so
            #    we don't need to check them. `population_accessions`
            #    rows likewise CASCADE.
            if accession_candidates:
                with db_engine.get_session() as session:
                    still_in_studies = set(session.execute(
                        select(
                            GenotypingStudySampleModel.accession_id
                        ).where(
                            GenotypingStudySampleModel.accession_id.in_(
                                accession_candidates
                            )
                        ).distinct()
                    ).scalars().all())
                    still_in_plots = set(session.execute(
                        select(PlotModel.accession_id).where(
                            PlotModel.accession_id.in_(accession_candidates)
                        ).distinct()
                    ).scalars().all())
                    orphan_accessions = [
                        a for a in accession_candidates
                        if a not in still_in_studies
                        and a not in still_in_plots
                    ]
                    if orphan_accessions:
                        session.execute(
                            AccessionModel.__table__.delete().where(
                                AccessionModel.id.in_(orphan_accessions)
                            )
                        )
                        session.commit()
                        logger.info(
                            "Deleted %d orphan accession(s) after "
                            "deleting study %s.",
                            len(orphan_accessions), self.study_name,
                        )
            return True
        except Exception as e:
            logger.error(f"Error deleting genotyping study: {e}")
            return False

    def refresh(self) -> Optional["GenotypingStudy"]:
        try:
            db_instance = GenotypingStudyModel.get(self.id)
            if not db_instance:
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing genotyping study: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        try:
            db_instance = GenotypingStudyModel.get(self.id)
            if not db_instance:
                return None
            return db_instance.study_info
        except Exception as e:
            logger.error(f"Error getting study info: {e}")
            return None

    def set_info(self, study_info: dict) -> Optional["GenotypingStudy"]:
        try:
            db_instance = GenotypingStudyModel.get(self.id)
            if not db_instance:
                return None
            db_instance = GenotypingStudyModel.update(db_instance, study_info=study_info)
            self.refresh()
            return self.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error setting study info: {e}")
            return None

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        try:
            from gemini.api.experiment import Experiment
            results = ExperimentGenotypingStudiesViewModel.search(study_id=self.id)
            if not results or len(results) == 0:
                return None
            return [Experiment.model_validate(r) for r in results]
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                return None
            existing = ExperimentGenotypingStudyModel.get_by_parameters(
                experiment_id=experiment.id,
                study_id=self.id,
            )
            if existing:
                return experiment
            ExperimentGenotypingStudyModel.get_or_create(
                experiment_id=experiment.id,
                study_id=self.id,
            )
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating genotyping study with experiment: {e}")
            return None

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                return None
            existing = ExperimentGenotypingStudyModel.get_by_parameters(
                experiment_id=experiment.id,
                study_id=self.id,
            )
            if not existing:
                return None
            ExperimentGenotypingStudyModel.delete(existing)
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating genotyping study from experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                return False
            return ExperimentGenotypingStudyModel.exists(
                experiment_id=experiment.id,
                study_id=self.id,
            )
        except Exception as e:
            logger.error(f"Error checking if genotyping study belongs to experiment: {e}")
            return False

    def export(self, format: str = "hapmap", coding: str = "012") -> str:
        """Phase 9d': export the study via PLINK2 from its MinIO PGEN.

        Replaces the legacy tall-table export, which materialised every
        (variant, accession, call) row into Python and built per-format
        text by hand. PLINK2's ``--export`` is the reference exporter
        for HapMap, VCF, and PLINK; for "numeric" we map onto its
        ``--export A-transpose`` (additive coding) which matches the
        old 0/1/2 output.

        Looks up the study's PGEN file pointer in
        ``genotyping_study_files``, downloads it to a temp dir
        alongside its .pvar / .psam sidecars, runs the right
        ``plink2 --export``, returns the resulting text.
        """
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path

        from gemini.api.base import minio_storage_provider
        from gemini.db.core.base import db_engine
        from gemini.db.models.genotyping_study_files import (
            GenotypingStudyFileModel,
        )
        from sqlalchemy import select

        with db_engine.get_session() as session:
            files = {
                row.file_kind: row.s3_uri
                for row in session.execute(
                    select(GenotypingStudyFileModel).where(
                        GenotypingStudyFileModel.study_id == self.id
                    )
                ).scalars()
            }
        if "pgen" not in files:
            logger.warning(
                "No PGEN file pointer for study '%s'; nothing to export.",
                self.study_name,
            )
            return ""

        # Map app-level format name → plink2 --export argument + ext.
        # plink2 supports vcf, ped (PLINK1), tped, A (additive 0/1/2)
        # natively in v2.0.0-a.6. HapMap isn't built in, so we ask for
        # tped (transposed PED) which is the closest off-the-shelf
        # variant-per-row format. Callers wanting strict HapMap can
        # post-process the tped or use the new variant browser.
        export_args = {
            "vcf":    ["--export", "vcf"],
            "plink":  ["--export", "ped"],
            "numeric": ["--export", "A"],
            # `hapmap` aliased to tped — same shape (rs#, alleles,
            # chrom, pos, then per-sample columns); not bit-for-bit
            # equivalent to TASSEL HapMap but downstream-compatible
            # with most breeding tools.
            "hapmap": ["--export", "tped"],
        }
        if format not in export_args:
            raise ValueError(f"Unsupported export format: {format}")

        with tempfile.TemporaryDirectory(
            prefix=f"gemini-export-{self.id}-",
        ) as tmp:
            work = Path(tmp)
            # Download the trio. plink2 --pfile expects all three side
            # by side under the same prefix.
            for kind in ("pgen", "pvar", "psam"):
                uri = files.get(kind)
                if not uri:
                    raise ValueError(
                        f"Study {self.study_name} is missing its .{kind} "
                        f"file pointer; can't export."
                    )
                bucket, _, object_name = uri.removeprefix("s3://").partition("/")
                local = work / f"geno.{kind}"
                minio_storage_provider.client.fget_object(
                    bucket_name=bucket,
                    object_name=object_name,
                    file_path=str(local),
                )
            out_prefix = work / "out"
            cmd = [
                "plink2",
                "--pfile", str(work / "geno"),
                *export_args[format],
                "--out", str(out_prefix),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(
                    f"plink2 --export {format} failed (exit "
                    f"{res.returncode}): {res.stderr[:1000]}"
                )

            # Pick the produced file and return its bytes as text.
            # plink2 writes a primary text file plus a sidecar (.map/.tfam/etc).
            # Map name → primary ext.
            out_ext = {
                "vcf": ".vcf",
                "plink": ".ped",
                "numeric": ".raw",
                "hapmap": ".tped",
            }
            primary = (work / "out").with_suffix(out_ext[format])
            if not primary.exists():
                candidates = sorted(
                    p for p in work.glob("out.*") if p.suffix != ".log"
                )
                if not candidates:
                    raise RuntimeError(
                        f"plink2 --export {format} produced no output file "
                        f"in {work} (saw: "
                        f"{[p.name for p in work.iterdir()]})"
                    )
                primary = candidates[0]
            return primary.read_text()

    def _export_hapmap(self, variant_list, variants, sample_list, matrix):
        lines = []
        header = ["rs#", "alleles", "chrom", "pos", "strand", "assembly#",
                  "center", "protLSID", "assayLSID", "panelLSID", "QCcode"] + sample_list
        lines.append("\t".join(header))
        for vname in variant_list:
            v = variants[vname]
            row = [vname, v.get("alleles", ""), str(v["chromosome"]),
                   str(v["position"]), "+", "NA", "NA", "NA", "NA", "NA", "NA"]
            for s in sample_list:
                call = matrix.get((vname, s), "NN")
                if len(call) == 2 and call[0] == call[1]:
                    row.append(call[0])
                else:
                    row.append(call)
            lines.append("\t".join(row))
        return "\n".join(lines) + "\n"

    def _export_vcf(self, variant_list, variants, sample_list, matrix):
        lines = []
        lines.append("##fileformat=VCFv4.3")
        lines.append(f"##source=GEMINI-{self.study_name}")
        header = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"] + sample_list
        lines.append("\t".join(header))
        for vname in variant_list:
            v = variants[vname]
            allele_parts = v.get("alleles", "/").split("/")
            ref = allele_parts[0] if len(allele_parts) > 0 else "."
            alt = allele_parts[1] if len(allele_parts) > 1 else "."
            row = [str(v["chromosome"]), str(int(v["position"])), vname, ref, alt, ".", "PASS", ".", "GT"]
            for s in sample_list:
                call = matrix.get((vname, s), "")
                if not call:
                    row.append("./.")
                elif len(call) == 2:
                    a1, a2 = call[0], call[1]
                    g1 = "0" if a1 == ref else "1"
                    g2 = "0" if a2 == ref else "1"
                    row.append(f"{g1}/{g2}")
                else:
                    row.append("./.")
            lines.append("\t".join(row))
        return "\n".join(lines) + "\n"

    def _export_numeric(self, variant_list, variants, sample_list, matrix, coding="012"):
        lines = []
        header = ["taxa"] + variant_list
        lines.append("\t".join(header))
        for s in sample_list:
            row = [s]
            for vname in variant_list:
                call = matrix.get((vname, s), "")
                v = variants[vname]
                allele_parts = v.get("alleles", "/").split("/")
                ref = allele_parts[0] if len(allele_parts) > 0 else ""
                if not call:
                    row.append("-1" if coding == "012" else "-2")
                elif len(call) == 2:
                    alt_count = sum(1 for a in call if a != ref)
                    if coding == "012":
                        row.append(str(alt_count))
                    else:
                        row.append(str(alt_count - 1))
                else:
                    row.append("-1" if coding == "012" else "-2")
            lines.append("\t".join(row))
        return "\n".join(lines) + "\n"

    def _export_plink(self, variant_list, variants, sample_list, matrix):
        ped_lines = []
        map_lines = []
        for s in sample_list:
            row = [s, s, "0", "0", "0", "-9"]
            for vname in variant_list:
                call = matrix.get((vname, s), "")
                if len(call) == 2:
                    row.extend([call[0], call[1]])
                else:
                    row.extend(["0", "0"])
            ped_lines.append("\t".join(row))
        for vname in variant_list:
            v = variants[vname]
            map_lines.append(f"{v['chromosome']}\t{vname}\t{v['position']}\t0")
        ped_content = "\n".join(ped_lines) + "\n"
        map_content = "\n".join(map_lines) + "\n"
        return f"# PED\n{ped_content}# MAP\n{map_content}"
