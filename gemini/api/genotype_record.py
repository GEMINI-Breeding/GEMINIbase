"""
This module defines the GenotypeRecord class, which represents a genotype call record
(one variant observed in one sample within a genotyping study).

It includes methods for creating, retrieving, updating, deleting, bulk-inserting,
and filtering genotype records.
"""

from typing import Optional, List, Generator
from uuid import UUID

import logging
from gemini.api.types import ID
from pydantic import Field, AliasChoices
from gemini.api.base import APIBase
from gemini.db.models.columnar.genotype_records import GenotypeRecordModel

logger = logging.getLogger(__name__)


class GenotypeRecord(APIBase):
    """
    Represents a genotype call record.

    Attributes:
        id (Optional[ID]): The unique identifier of the record.
        genotype_id (Optional[ID]): The ID of the genotyping study.
        genotype_name (Optional[str]): The name of the genotyping study.
        variant_id (Optional[ID]): The ID of the variant.
        variant_name (Optional[str]): The name of the variant.
        chromosome (Optional[int]): Chromosome number.
        position (Optional[float]): Genetic map position (cM).
        population_id (Optional[ID]): The ID of the population/sample.
        population_name (Optional[str]): The name of the population.
        population_accession (Optional[str]): The accession of the population.
        call_value (Optional[str]): The genotype call (e.g. "AA", "TT").
        record_info (Optional[dict]): Additional information.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "genotype_record_id"))

    genotype_id: Optional[ID] = None
    genotype_name: Optional[str] = None
    variant_id: Optional[ID] = None
    variant_name: Optional[str] = None
    chromosome: Optional[int] = None
    position: Optional[float] = None
    population_id: Optional[ID] = None
    population_name: Optional[str] = None
    population_accession: Optional[str] = None
    call_value: Optional[str] = None
    record_info: Optional[dict] = None

    def __str__(self):
        return f"GenotypeRecord(id={self.id}, genotype_name={self.genotype_name}, variant_name={self.variant_name}, population_name={self.population_name}, call_value={self.call_value})"

    def __repr__(self):
        return f"GenotypeRecord(id={self.id}, genotype_name={self.genotype_name}, variant_name={self.variant_name}, population_name={self.population_name}, call_value={self.call_value})"

    @classmethod
    def exists(
        cls,
        genotype_name: str,
        variant_name: str,
        population_name: str,
    ) -> bool:
        try:
            return GenotypeRecordModel.exists(
                genotype_name=genotype_name,
                variant_name=variant_name,
                population_name=population_name,
            )
        except Exception as e:
            logger.error(f"Error checking existence of GenotypeRecord: {e}")
            return False

    @classmethod
    def create(
        cls,
        genotype_id: UUID = None,
        genotype_name: str = None,
        variant_id: UUID = None,
        variant_name: str = None,
        chromosome: int = None,
        position: float = None,
        population_id: UUID = None,
        population_name: str = None,
        population_accession: str = None,
        call_value: str = None,
        record_info: dict = None,
    ) -> Optional["GenotypeRecord"]:
        try:
            if not genotype_name:
                raise ValueError("Genotype name is required.")
            if not variant_name:
                raise ValueError("Variant name is required.")
            if not population_name:
                raise ValueError("Population name is required.")
            if not call_value:
                raise ValueError("Call value is required.")

            record = GenotypeRecord(
                genotype_id=genotype_id,
                genotype_name=genotype_name,
                variant_id=variant_id,
                variant_name=variant_name,
                chromosome=chromosome,
                position=position,
                population_id=population_id,
                population_name=population_name,
                population_accession=population_accession,
                call_value=call_value,
                record_info=record_info or {},
            )
            success, ids = cls.insert([record])
            if not success or not ids:
                return None
            return cls.get_by_id(ids[0])
        except Exception as e:
            logger.error(f"Error creating GenotypeRecord: {e}")
            return None

    @classmethod
    def insert(cls, records: List["GenotypeRecord"]) -> tuple[bool, List[str]]:
        """
        Bulk-insert genotype records.

        Args:
            records: List of GenotypeRecord instances.
        Returns:
            Tuple of (success, list of inserted IDs).
        """
        try:
            if not records:
                return False, []
            records_to_insert = []
            for record in records:
                record_dict = record.model_dump()
                record_dict = {k: v for k, v in record_dict.items() if v is not None}
                records_to_insert.append(record_dict)
            logger.info(f"Inserting {len(records_to_insert)} GenotypeRecords.")
            inserted_ids = GenotypeRecordModel.insert_bulk('genotype_records_unique', records_to_insert)
            logger.info(f"Inserted {len(inserted_ids)} GenotypeRecords.")
            return True, inserted_ids
        except Exception as e:
            logger.error(f"Error inserting GenotypeRecords: {e}")
            return False, []

    @classmethod
    def get(
        cls,
        genotype_name: str,
        variant_name: str,
        population_name: str,
    ) -> Optional["GenotypeRecord"]:
        try:
            db_instance = GenotypeRecordModel.get_by_parameters(
                genotype_name=genotype_name,
                variant_name=variant_name,
                population_name=population_name,
            )
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting GenotypeRecord: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["GenotypeRecord"]:
        try:
            db_instance = GenotypeRecordModel.get(id)
            if not db_instance:
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting GenotypeRecord by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = 100) -> Optional[List["GenotypeRecord"]]:
        try:
            records = GenotypeRecordModel.all(limit=limit)
            if not records or len(records) == 0:
                return None
            return [cls.model_validate(r) for r in records]
        except Exception as e:
            logger.error(f"Error getting all GenotypeRecords: {e}")
            return None

    @classmethod
    def search(
        cls,
        genotype_name: str = None,
        variant_name: str = None,
        population_name: str = None,
        chromosome: int = None,
        call_value: str = None,
        record_info: dict = None,
    ) -> Optional[List["GenotypeRecord"]]:
        try:
            if not any([genotype_name, variant_name, population_name, chromosome, call_value, record_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            records = GenotypeRecordModel.search(
                genotype_name=genotype_name,
                variant_name=variant_name,
                population_name=population_name,
                chromosome=chromosome,
                call_value=call_value,
                record_info=record_info,
            )
            if not records or len(records) == 0:
                return None
            return [cls.model_validate(r) for r in records]
        except Exception as e:
            logger.error(f"Error searching GenotypeRecords: {e}")
            return None

    @classmethod
    def filter(
        cls,
        genotype_names: Optional[List[str]] = None,
        variant_names: Optional[List[str]] = None,
        population_names: Optional[List[str]] = None,
        chromosomes: Optional[List[int]] = None,
    ) -> Generator["GenotypeRecord", None, None]:
        """
        Filter genotype records using the database filter function.

        Args:
            genotype_names: Genotyping study names to filter by.
            variant_names: Variant/marker names to filter by.
            population_names: Population/sample names to filter by.
            chromosomes: Chromosome numbers to filter by.
        Yields:
            GenotypeRecord: Matching records.
        """
        try:
            if not any([genotype_names, variant_names, population_names, chromosomes]):
                logger.warning("At least one filter parameter must be provided.")
                return
            records = GenotypeRecordModel.filter_records(
                genotype_names=genotype_names,
                variant_names=variant_names,
                population_names=population_names,
                chromosomes=chromosomes,
            )
            for record in records:
                yield cls.model_validate(record)
        except Exception as e:
            logger.error(f"Error filtering GenotypeRecords: {e}")
            yield from []

    def update(
        self,
        call_value: str = None,
        record_info: dict = None,
    ) -> Optional["GenotypeRecord"]:
        try:
            if not any([call_value, record_info]):
                logger.warning("At least one parameter must be provided to update.")
                return None
            db_instance = GenotypeRecordModel.get(self.id)
            if not db_instance:
                return None
            db_instance = GenotypeRecordModel.update(
                db_instance,
                call_value=call_value,
                record_info=record_info,
            )
            record = self.model_validate(db_instance)
            self.refresh()
            return record
        except Exception as e:
            logger.error(f"Error updating GenotypeRecord: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = GenotypeRecordModel.get(self.id)
            if not db_instance:
                return False
            GenotypeRecordModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting GenotypeRecord: {e}")
            return False

    def refresh(self) -> Optional["GenotypeRecord"]:
        try:
            db_instance = GenotypeRecordModel.get(self.id)
            if not db_instance:
                return None
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing GenotypeRecord: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        try:
            db_instance = GenotypeRecordModel.get(self.id)
            if not db_instance:
                return None
            return db_instance.record_info
        except Exception as e:
            logger.error(f"Error getting record info: {e}")
            return None

    def set_info(self, record_info: dict) -> Optional["GenotypeRecord"]:
        try:
            db_instance = GenotypeRecordModel.get(self.id)
            if not db_instance:
                return None
            GenotypeRecordModel.update(db_instance, record_info=record_info)
            record = self.model_validate(db_instance)
            self.refresh()
            return record
        except Exception as e:
            logger.error(f"Error setting record info: {e}")
            return None
