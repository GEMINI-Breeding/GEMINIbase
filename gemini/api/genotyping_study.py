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
from gemini.db.models.columnar.genotype_records import GenotypeRecordModel

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
                study.associate_experiment(experiment_name)
            return study
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
        try:
            from sqlalchemy import select
            from gemini.db.core.base import db_engine
            from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
            from gemini.db.models.variants import VariantModel

            db_instance = GenotypingStudyModel.get(self.id)
            if not db_instance:
                return False

            # genotype_records.study_id has no FK constraint (columnar),
            # so we must clean it explicitly.
            with db_engine.get_session() as session:
                # Collect variant_ids referenced by this study BEFORE the
                # records go away so we can sweep variants that no other
                # study touches. Variants are a shared catalog (same SNP
                # can live in multiple studies), so the cascade is
                # conditional: only variants with zero remaining record
                # references are deleted.
                variant_candidates = list(set(session.execute(
                    select(GenotypeRecordModel.variant_id).where(
                        GenotypeRecordModel.study_id == self.id
                    )
                ).scalars().all()))

                deleted = session.execute(
                    GenotypeRecordModel.__table__.delete().where(
                        GenotypeRecordModel.study_id == self.id
                    )
                ).rowcount
                if deleted:
                    logger.info(
                        f"Deleted {deleted} genotype_record(s) for "
                        f"study {self.study_name}."
                    )

                if variant_candidates:
                    still_ref = set(session.execute(
                        select(GenotypeRecordModel.variant_id).where(
                            GenotypeRecordModel.variant_id.in_(variant_candidates)
                        ).distinct()
                    ).scalars().all())
                    orphan_variants = [
                        v for v in variant_candidates if v not in still_ref
                    ]
                    if orphan_variants:
                        session.execute(
                            VariantModel.__table__.delete().where(
                                VariantModel.id.in_(orphan_variants)
                            )
                        )
                        logger.info(
                            f"Deleted {len(orphan_variants)} orphan variant(s) "
                            f"after deleting study {self.study_name}."
                        )

            GenotypingStudyModel.delete(db_instance)
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
        records = list(GenotypeRecordModel.filter_records(
            study_names=[self.study_name]
        ))

        if not records:
            logger.warning(f"No genotype records found for '{self.study_name}'.")
            return ""

        variants = {}
        samples = set()
        matrix = {}

        for r in records:
            vname = r.variant_name
            sname = r.accession_name
            if vname not in variants:
                variants[vname] = {
                    "chromosome": r.chromosome,
                    "position": r.position,
                    "alleles": getattr(r, 'alleles', ''),
                }
            samples.add(sname)
            matrix[(vname, sname)] = r.call_value

        sample_list = sorted(samples)
        variant_list = sorted(variants.keys(), key=lambda v: (variants[v]["chromosome"], variants[v]["position"]))

        if format == "hapmap":
            return self._export_hapmap(variant_list, variants, sample_list, matrix)
        elif format == "vcf":
            return self._export_vcf(variant_list, variants, sample_list, matrix)
        elif format == "numeric":
            return self._export_numeric(variant_list, variants, sample_list, matrix, coding)
        elif format == "plink":
            return self._export_plink(variant_list, variants, sample_list, matrix)
        else:
            raise ValueError(f"Unsupported export format: {format}")

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
