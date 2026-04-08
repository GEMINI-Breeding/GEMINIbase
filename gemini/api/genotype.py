"""
This module defines the Genotype class, which represents a genotyping study/protocol
in the Gemini API.

It provides methods to create, retrieve, update, delete, and manage genotyping studies,
as well as to associate them with experiments and export data in standard formats.
"""

from typing import Optional, List
from uuid import UUID
import io

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.genotypes import GenotypeModel
from gemini.db.models.associations import ExperimentGenotypeModel
from gemini.db.models.views.genotype_views import ExperimentGenotypesViewModel
from gemini.db.models.columnar.genotype_records import GenotypeRecordModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemini.api.experiment import Experiment

logger = logging.getLogger(__name__)


class Genotype(APIBase):
    """
    Represents a genotyping study or protocol.

    Attributes:
        id (Optional[ID]): The unique identifier of the genotype study.
        genotype_name (str): The name of the genotyping study.
        genotype_info (Optional[dict]): Additional information (reference genome, platform, etc.).
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "genotype_id"))

    genotype_name: str
    genotype_info: Optional[dict] = None

    def __str__(self):
        return f"Genotype(genotype_name={self.genotype_name}, id={self.id})"

    def __repr__(self):
        return f"Genotype(genotype_name={self.genotype_name}, id={self.id})"

    @classmethod
    def exists(cls, genotype_name: str) -> bool:
        try:
            return GenotypeModel.exists(genotype_name=genotype_name)
        except Exception as e:
            logger.error(f"Error checking existence of genotype: {e}")
            return False

    @classmethod
    def create(
        cls,
        genotype_name: str,
        genotype_info: dict = None,
        experiment_name: str = None,
    ) -> Optional["Genotype"]:
        try:
            db_instance = GenotypeModel.get_or_create(
                genotype_name=genotype_name,
                genotype_info=genotype_info,
            )
            genotype = cls.model_validate(db_instance)
            if experiment_name:
                genotype.associate_experiment(experiment_name)
            return genotype
        except Exception as e:
            logger.error(f"Error creating genotype: {e}")
            return None

    @classmethod
    def get(cls, genotype_name: str, experiment_name: str = None) -> Optional["Genotype"]:
        try:
            if experiment_name:
                db_instance = ExperimentGenotypesViewModel.get_by_parameters(
                    genotype_name=genotype_name,
                    experiment_name=experiment_name,
                )
            else:
                db_instance = GenotypeModel.get_by_parameters(genotype_name=genotype_name)
            if not db_instance:
                logger.debug(f"Genotype '{genotype_name}' not found.")
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting genotype: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Genotype"]:
        try:
            db_instance = GenotypeModel.get(id)
            if not db_instance:
                logger.warning(f"Genotype with ID {id} does not exist.")
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting genotype by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Genotype"]]:
        try:
            genotypes = GenotypeModel.all(limit=limit, offset=offset)
            if not genotypes or len(genotypes) == 0:
                logger.info("No genotypes found.")
                return None
            return [cls.model_validate(g) for g in genotypes]
        except Exception as e:
            logger.error(f"Error getting all genotypes: {e}")
            return None

    @classmethod
    def search(
        cls,
        genotype_name: str = None,
        genotype_info: dict = None,
        experiment_name: str = None,
    ) -> Optional[List["Genotype"]]:
        try:
            if not any([genotype_name, genotype_info, experiment_name]):
                logger.warning("At least one search parameter must be provided.")
                return None
            genotypes = ExperimentGenotypesViewModel.search(
                genotype_name=genotype_name,
                genotype_info=genotype_info,
                experiment_name=experiment_name,
            )
            if not genotypes or len(genotypes) == 0:
                logger.info("No genotypes found with the provided search parameters.")
                return None
            return [cls.model_validate(g) for g in genotypes]
        except Exception as e:
            logger.error(f"Error searching genotypes: {e}")
            return None

    def update(
        self,
        genotype_name: str = None,
        genotype_info: dict = None,
    ) -> Optional["Genotype"]:
        try:
            if not any([genotype_name, genotype_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            db_instance = GenotypeModel.get(self.id)
            if not db_instance:
                logger.warning(f"Genotype with ID {self.id} does not exist.")
                return None
            db_instance = GenotypeModel.update(
                db_instance,
                genotype_name=genotype_name,
                genotype_info=genotype_info,
            )
            genotype = self.model_validate(db_instance)
            self.refresh()
            return genotype
        except Exception as e:
            logger.error(f"Error updating genotype: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = GenotypeModel.get(self.id)
            if not db_instance:
                logger.warning(f"Genotype with ID {self.id} does not exist.")
                return False
            GenotypeModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting genotype: {e}")
            return False

    def refresh(self) -> Optional["Genotype"]:
        try:
            db_instance = GenotypeModel.get(self.id)
            if not db_instance:
                logger.warning(f"Genotype with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing genotype: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        try:
            db_instance = GenotypeModel.get(self.id)
            if not db_instance:
                return None
            return db_instance.genotype_info
        except Exception as e:
            logger.error(f"Error getting genotype info: {e}")
            return None

    def set_info(self, genotype_info: dict) -> Optional["Genotype"]:
        try:
            db_instance = GenotypeModel.get(self.id)
            if not db_instance:
                return None
            db_instance = GenotypeModel.update(db_instance, genotype_info=genotype_info)
            genotype = self.model_validate(db_instance)
            self.refresh()
            return genotype
        except Exception as e:
            logger.error(f"Error setting genotype info: {e}")
            return None

    # -- Experiment associations --

    def get_associated_experiments(self) -> Optional[List["Experiment"]]:
        try:
            from gemini.api.experiment import Experiment
            experiment_genotypes = ExperimentGenotypesViewModel.search(genotype_id=self.id)
            if not experiment_genotypes or len(experiment_genotypes) == 0:
                logger.info("No associated experiments found.")
                return None
            return [Experiment.model_validate(eg) for eg in experiment_genotypes]
        except Exception as e:
            logger.error(f"Error getting associated experiments: {e}")
            return None

    def associate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing = ExperimentGenotypeModel.get_by_parameters(
                experiment_id=experiment.id,
                genotype_id=self.id,
            )
            if existing:
                logger.info(f"Genotype {self.genotype_name} already associated with experiment {experiment_name}.")
                return experiment
            ExperimentGenotypeModel.get_or_create(
                experiment_id=experiment.id,
                genotype_id=self.id,
            )
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error associating genotype with experiment: {e}")
            return None

    def unassociate_experiment(self, experiment_name: str) -> Optional["Experiment"]:
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} does not exist.")
                return None
            existing = ExperimentGenotypeModel.get_by_parameters(
                experiment_id=experiment.id,
                genotype_id=self.id,
            )
            if not existing:
                logger.info(f"Genotype {self.genotype_name} is not associated with experiment {experiment_name}.")
                return None
            ExperimentGenotypeModel.delete(existing)
            self.refresh()
            return experiment
        except Exception as e:
            logger.error(f"Error unassociating genotype from experiment: {e}")
            return None

    def belongs_to_experiment(self, experiment_name: str) -> bool:
        try:
            from gemini.api.experiment import Experiment
            experiment = Experiment.get(experiment_name=experiment_name)
            if not experiment:
                return False
            return ExperimentGenotypeModel.exists(
                experiment_id=experiment.id,
                genotype_id=self.id,
            )
        except Exception as e:
            logger.error(f"Error checking if genotype belongs to experiment: {e}")
            return False

    # -- Export methods --

    def export(self, format: str = "hapmap", coding: str = "012") -> str:
        """
        Export genotype data in a standard file format.

        Args:
            format: Export format - "hapmap", "vcf", "numeric", or "plink".
            coding: For numeric format, "012" or "-101".
        Returns:
            String content of the exported file.
        """
        records = list(GenotypeRecordModel.filter_records(
            genotype_names=[self.genotype_name]
        ))

        if not records:
            logger.warning(f"No genotype records found for '{self.genotype_name}'.")
            return ""

        # Build variant x sample matrix
        variants = {}  # variant_name -> {chromosome, position, alleles}
        samples = set()
        matrix = {}  # (variant_name, population_name) -> call_value

        for r in records:
            vname = r.variant_name
            pname = r.population_name
            if vname not in variants:
                variants[vname] = {
                    "chromosome": r.chromosome,
                    "position": r.position,
                    "alleles": getattr(r, 'alleles', ''),
                }
            samples.add(pname)
            matrix[(vname, pname)] = r.call_value

        sample_list = sorted(samples)
        # Sort variants by chromosome then position
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
                # Convert diploid call (e.g. "AA") to single IUPAC letter for homozygous
                if len(call) == 2 and call[0] == call[1]:
                    row.append(call[0])
                else:
                    row.append(call)
            lines.append("\t".join(row))

        return "\n".join(lines) + "\n"

    def _export_vcf(self, variant_list, variants, sample_list, matrix):
        lines = []
        lines.append("##fileformat=VCFv4.3")
        lines.append(f"##source=GEMINI-{self.genotype_name}")
        header = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"] + sample_list
        lines.append("\t".join(header))

        for vname in variant_list:
            v = variants[vname]
            allele_parts = v.get("alleles", "/").split("/")
            ref = allele_parts[0] if len(allele_parts) > 0 else "."
            alt = allele_parts[1] if len(allele_parts) > 1 else "."
            row = [str(v["chromosome"]), str(int(v["position"])), vname,
                   ref, alt, ".", "PASS", ".", "GT"]
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
                    else:  # -101
                        row.append(str(alt_count - 1))
                else:
                    row.append("-1" if coding == "012" else "-2")
            lines.append("\t".join(row))

        return "\n".join(lines) + "\n"

    def _export_plink(self, variant_list, variants, sample_list, matrix):
        """Export as Plink PED + MAP combined (PED\\n---\\nMAP)."""
        ped_lines = []
        map_lines = []

        for s in sample_list:
            # PED: FID IID paternal maternal sex phenotype genotypes...
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
            # MAP: chromosome, variant_id, cM_position, bp_position
            map_lines.append(f"{v['chromosome']}\t{vname}\t{v['position']}\t0")

        ped_content = "\n".join(ped_lines) + "\n"
        map_content = "\n".join(map_lines) + "\n"
        return f"# PED\n{ped_content}# MAP\n{map_content}"
