"""
This module defines the GenotypeRecord class, which represents a genotype call record
(one variant observed in one accession within a genotyping study).
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

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "genotype_record_id"))

    study_id: Optional[ID] = None
    study_name: Optional[str] = None
    variant_id: Optional[ID] = None
    variant_name: Optional[str] = None
    chromosome: Optional[int] = None
    position: Optional[float] = None
    accession_id: Optional[ID] = None
    accession_name: Optional[str] = None
    call_value: Optional[str] = None
    record_info: Optional[dict] = None

    def __str__(self):
        return f"GenotypeRecord(id={self.id}, study_name={self.study_name}, variant_name={self.variant_name}, accession_name={self.accession_name}, call_value={self.call_value})"

    def __repr__(self):
        return f"GenotypeRecord(id={self.id}, study_name={self.study_name}, variant_name={self.variant_name}, accession_name={self.accession_name}, call_value={self.call_value})"

    @classmethod
    def exists(
        cls,
        study_name: str,
        variant_name: str,
        accession_name: str,
    ) -> bool:
        try:
            return GenotypeRecordModel.exists(
                study_name=study_name,
                variant_name=variant_name,
                accession_name=accession_name,
            )
        except Exception as e:
            logger.error(f"Error checking existence of GenotypeRecord: {e}")
            return False

    @classmethod
    def create(
        cls,
        study_id: UUID = None,
        study_name: str = None,
        variant_id: UUID = None,
        variant_name: str = None,
        chromosome: int = None,
        position: float = None,
        accession_id: UUID = None,
        accession_name: str = None,
        call_value: str = None,
        record_info: dict = None,
    ) -> Optional["GenotypeRecord"]:
        try:
            if not study_name:
                raise ValueError("Study name is required.")
            if not variant_name:
                raise ValueError("Variant name is required.")
            if not accession_name:
                raise ValueError("Accession name is required.")
            if not call_value:
                raise ValueError("Call value is required.")

            record = GenotypeRecord(
                study_id=study_id,
                study_name=study_name,
                variant_id=variant_id,
                variant_name=variant_name,
                chromosome=chromosome,
                position=position,
                accession_id=accession_id,
                accession_name=accession_name,
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
        study_name: str,
        variant_name: str,
        accession_name: str,
    ) -> Optional["GenotypeRecord"]:
        try:
            db_instance = GenotypeRecordModel.get_by_parameters(
                study_name=study_name,
                variant_name=variant_name,
                accession_name=accession_name,
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
        study_name: str = None,
        variant_name: str = None,
        accession_name: str = None,
        chromosome: int = None,
        call_value: str = None,
        record_info: dict = None,
    ) -> Optional[List["GenotypeRecord"]]:
        try:
            if not any([study_name, variant_name, accession_name, chromosome, call_value, record_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            records = GenotypeRecordModel.search(
                study_name=study_name,
                variant_name=variant_name,
                accession_name=accession_name,
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
        study_names: Optional[List[str]] = None,
        variant_names: Optional[List[str]] = None,
        accession_names: Optional[List[str]] = None,
        chromosomes: Optional[List[int]] = None,
    ) -> Generator["GenotypeRecord", None, None]:
        try:
            if not any([study_names, variant_names, accession_names, chromosomes]):
                logger.warning("At least one filter parameter must be provided.")
                return
            records = GenotypeRecordModel.filter_records(
                study_names=study_names,
                variant_names=variant_names,
                accession_names=accession_names,
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
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing GenotypeRecord: {e}")
            return None
