"""
This module defines the Variant class, which represents a genetic variant (marker/SNP)
in the Gemini API.

It provides methods to create, retrieve, update, delete, and search variants,
as well as bulk creation for loading large marker sets.
"""

from typing import Optional, List
from uuid import UUID

from pydantic import Field, AliasChoices
import logging
from gemini.api.types import ID
from gemini.api.base import APIBase
from gemini.db.models.variants import VariantModel

logger = logging.getLogger(__name__)


class Variant(APIBase):
    """
    Represents a genetic variant (marker/SNP).

    Attributes:
        id (Optional[ID]): The unique identifier of the variant.
        variant_name (str): The name/identifier of the variant (e.g. "2_24641").
        chromosome (int): Chromosome number.
        position (float): Genetic map position in centiMorgans (cM).
        alleles (str): SNP alleles in "ref/alt" format (e.g. "T/C").
        design_sequence (Optional[str]): Flanking sequence with variant marked.
        variant_info (Optional[dict]): Additional information about the variant.
    """

    id: Optional[ID] = Field(None, validation_alias=AliasChoices("id", "variant_id"))

    variant_name: str
    chromosome: int
    position: float
    alleles: str
    design_sequence: Optional[str] = None
    variant_info: Optional[dict] = None

    def __str__(self):
        return f"Variant(variant_name={self.variant_name}, chromosome={self.chromosome}, position={self.position}, alleles={self.alleles}, id={self.id})"

    def __repr__(self):
        return f"Variant(variant_name={self.variant_name}, chromosome={self.chromosome}, position={self.position}, alleles={self.alleles}, id={self.id})"

    @classmethod
    def exists(cls, variant_name: str) -> bool:
        try:
            return VariantModel.exists(variant_name=variant_name)
        except Exception as e:
            logger.error(f"Error checking existence of variant: {e}")
            return False

    @classmethod
    def create(
        cls,
        variant_name: str,
        chromosome: int,
        position: float,
        alleles: str,
        design_sequence: str = '',
        variant_info: dict = None,
    ) -> Optional["Variant"]:
        try:
            db_instance = VariantModel.get_or_create(
                variant_name=variant_name,
                chromosome=chromosome,
                position=position,
                alleles=alleles,
                design_sequence=design_sequence,
                variant_info=variant_info,
            )
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error creating variant: {e}")
            return None

    @classmethod
    def create_bulk(cls, variants: List[dict]) -> tuple[bool, List[str]]:
        """
        Bulk-insert variants. Each dict should contain variant_name, chromosome,
        position, alleles, and optionally design_sequence and variant_info.

        Args:
            variants: List of variant dictionaries.
        Returns:
            Tuple of (success, list of inserted IDs).
        """
        try:
            if not variants:
                return False, []
            inserted_ids = VariantModel.insert_bulk('variant_unique', variants)
            logger.info(f"Bulk-inserted {len(inserted_ids)} variants.")
            return True, inserted_ids
        except Exception as e:
            logger.error(f"Error bulk-inserting variants: {e}")
            return False, []

    @classmethod
    def get(cls, variant_name: str) -> Optional["Variant"]:
        try:
            db_instance = VariantModel.get_by_parameters(variant_name=variant_name)
            if not db_instance:
                logger.debug(f"Variant '{variant_name}' not found.")
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting variant: {e}")
            return None

    @classmethod
    def get_by_id(cls, id: UUID | int | str) -> Optional["Variant"]:
        try:
            db_instance = VariantModel.get(id)
            if not db_instance:
                logger.warning(f"Variant with ID {id} does not exist.")
                return None
            return cls.model_validate(db_instance)
        except Exception as e:
            logger.error(f"Error getting variant by ID: {e}")
            return None

    @classmethod
    def get_all(cls, limit: int = None, offset: int = None) -> Optional[List["Variant"]]:
        try:
            variants = VariantModel.all(limit=limit, offset=offset)
            if not variants or len(variants) == 0:
                logger.info("No variants found.")
                return None
            return [cls.model_validate(v) for v in variants]
        except Exception as e:
            logger.error(f"Error getting all variants: {e}")
            return None

    @classmethod
    def search(
        cls,
        variant_name: str = None,
        chromosome: int = None,
        alleles: str = None,
        variant_info: dict = None,
    ) -> Optional[List["Variant"]]:
        try:
            if not any([variant_name, chromosome, alleles, variant_info]):
                logger.warning("At least one search parameter must be provided.")
                return None
            variants = VariantModel.search(
                variant_name=variant_name,
                chromosome=chromosome,
                alleles=alleles,
                variant_info=variant_info,
            )
            if not variants or len(variants) == 0:
                logger.info("No variants found with the provided search parameters.")
                return None
            return [cls.model_validate(v) for v in variants]
        except Exception as e:
            logger.error(f"Error searching variants: {e}")
            return None

    def update(
        self,
        variant_name: str = None,
        chromosome: int = None,
        position: float = None,
        alleles: str = None,
        design_sequence: str = None,
        variant_info: dict = None,
    ) -> Optional["Variant"]:
        try:
            if not any([variant_name, chromosome, position, alleles, design_sequence, variant_info]):
                logger.warning("At least one parameter must be provided for update.")
                return None
            db_instance = VariantModel.get(self.id)
            if not db_instance:
                logger.warning(f"Variant with ID {self.id} does not exist.")
                return None
            db_instance = VariantModel.update(
                db_instance,
                variant_name=variant_name,
                chromosome=chromosome,
                position=position,
                alleles=alleles,
                design_sequence=design_sequence,
                variant_info=variant_info,
            )
            variant = self.model_validate(db_instance)
            self.refresh()
            return variant
        except Exception as e:
            logger.error(f"Error updating variant: {e}")
            return None

    def delete(self) -> bool:
        try:
            db_instance = VariantModel.get(self.id)
            if not db_instance:
                logger.warning(f"Variant with ID {self.id} does not exist.")
                return False
            VariantModel.delete(db_instance)
            return True
        except Exception as e:
            logger.error(f"Error deleting variant: {e}")
            return False

    def refresh(self) -> Optional["Variant"]:
        try:
            db_instance = VariantModel.get(self.id)
            if not db_instance:
                logger.warning(f"Variant with ID {self.id} does not exist.")
                return self
            instance = self.model_validate(db_instance)
            for key, value in instance.model_dump().items():
                if hasattr(self, key) and key != "id":
                    setattr(self, key, value)
            return self
        except Exception as e:
            logger.error(f"Error refreshing variant: {e}")
            return None

    def get_info(self) -> Optional[dict]:
        try:
            db_instance = VariantModel.get(self.id)
            if not db_instance:
                return None
            return db_instance.variant_info
        except Exception as e:
            logger.error(f"Error getting variant info: {e}")
            return None

    def set_info(self, variant_info: dict) -> Optional["Variant"]:
        try:
            db_instance = VariantModel.get(self.id)
            if not db_instance:
                return None
            db_instance = VariantModel.update(db_instance, variant_info=variant_info)
            variant = self.model_validate(db_instance)
            self.refresh()
            return variant
        except Exception as e:
            logger.error(f"Error setting variant info: {e}")
            return None
