"""
SQLAlchemy model for columnar GenotypeRecord entities in the GEMINI database.
"""

from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import (
    UUID,
    String,
    Integer,
    Float,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text, bindparam
from gemini.db.core.base import ColumnarBaseModel, db_engine
import uuid
from typing import Optional, List


class GenotypeRecordModel(ColumnarBaseModel):
    """
    Represents a genotype call record in the GEMINI database.

    Each row represents a single allele call: one variant observed in one
    sample (population) within one genotyping study.

    Attributes:
        id (uuid.UUID): Unique identifier for the record.
        genotype_id (UUID): Reference to the genotyping study.
        genotype_name (str): Denormalized name of the genotyping study.
        variant_id (UUID): Reference to the variant/marker.
        variant_name (str): Denormalized name of the variant.
        chromosome (int): Chromosome number of the variant.
        position (float): Genetic map position (cM) of the variant.
        population_id (UUID): Reference to the population/sample.
        population_name (str): Denormalized name of the population.
        population_accession (str): Denormalized accession of the population.
        call_value (str): The genotype call (e.g. "AA", "TT", "CC", "GG").
        record_info (dict): Additional JSONB data for the record.
    """

    __tablename__ = "genotype_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    genotype_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    genotype_name: Mapped[str] = mapped_column(String(255))
    variant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    variant_name: Mapped[str] = mapped_column(String(255))
    chromosome: Mapped[int] = mapped_column(Integer)
    position: Mapped[float] = mapped_column(Float)
    population_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True))
    population_name: Mapped[str] = mapped_column(String(255))
    population_accession: Mapped[str] = mapped_column(String(255))
    call_value: Mapped[str] = mapped_column(String(10))
    record_info: Mapped[dict] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint(
            "genotype_id",
            "variant_id",
            "population_id",
            name="genotype_records_unique"
        ),
        Index("idx_genotype_records_genotype_variant", "genotype_id", "variant_id"),
        Index("idx_genotype_records_genotype_population", "genotype_id", "population_id"),
        Index("idx_genotype_records_chromosome", "chromosome"),
        Index("idx_genotype_records_record_info", "record_info", postgresql_using="GIN"),
    )

    @classmethod
    def filter_records(
        cls,
        genotype_names: Optional[List[str]] = None,
        variant_names: Optional[List[str]] = None,
        population_names: Optional[List[str]] = None,
        chromosomes: Optional[List[int]] = None,
    ):
        """
        Filters genotype records based on the provided parameters.

        Args:
            genotype_names (Optional[List[str]]): Genotyping study names to filter by.
            variant_names (Optional[List[str]]): Variant/marker names to filter by.
            population_names (Optional[List[str]]): Population/sample names to filter by.
            chromosomes (Optional[List[int]]): Chromosome numbers to filter by.

        Yields:
            record: Matching genotype records.
        """
        stmt = text(
            """
            SELECT * FROM gemini.filter_genotype_records(
                p_genotype_names => :genotype_names,
                p_variant_names => :variant_names,
                p_population_names => :population_names,
                p_chromosomes => :chromosomes
            )
            """
        ).bindparams(
            bindparam("genotype_names", value=genotype_names),
            bindparam("variant_names", value=variant_names),
            bindparam("population_names", value=population_names),
            bindparam("chromosomes", value=chromosomes),
        )

        with db_engine.get_session() as session:
            result = session.execute(stmt, execution_options={"yield_per": 1000})
            for record in result:
                yield record
