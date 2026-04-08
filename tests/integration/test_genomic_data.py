"""
Integration tests for genomic data entities (Variant, Genotype, GenotypeRecord)
against real PostgreSQL.

Requires: docker compose -f tests/docker-compose.test.yaml up -d
"""
import pytest

pytestmark = pytest.mark.integration


class TestVariantCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        v = VariantModel.create(
            variant_name="1_100",
            chromosome=1,
            position=10.5,
            alleles="T/C",
            design_sequence="AGAC[T/C]GACT",
        )
        assert v.variant_name == "1_100"
        assert v.chromosome == 1
        assert v.id is not None

    def test_unique_constraint(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        VariantModel.create(variant_name="1_200", chromosome=1, position=20.0, alleles="A/G")
        dup = VariantModel.get_or_create(variant_name="1_200", chromosome=1, position=20.0, alleles="A/G")
        assert len(VariantModel.search(variant_name="1_200")) == 1

    def test_get_by_parameters(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        VariantModel.create(variant_name="2_300", chromosome=2, position=30.0, alleles="C/T")
        found = VariantModel.get_by_parameters(variant_name="2_300")
        assert found is not None
        assert found.chromosome == 2

    def test_search_by_chromosome(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        VariantModel.create(variant_name="3_100", chromosome=3, position=10.0, alleles="A/G")
        VariantModel.create(variant_name="3_200", chromosome=3, position=20.0, alleles="T/C")
        VariantModel.create(variant_name="4_100", chromosome=4, position=10.0, alleles="G/A")
        results = VariantModel.search(chromosome=3)
        assert len(results) == 2

    def test_update(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        v = VariantModel.create(variant_name="5_100", chromosome=5, position=10.0, alleles="A/T")
        VariantModel.update(v, variant_info={"note": "updated"})
        refreshed = VariantModel.get(v.id)
        assert refreshed.variant_info == {"note": "updated"}

    def test_delete(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        v = VariantModel.create(variant_name="6_100", chromosome=6, position=10.0, alleles="C/G")
        VariantModel.delete(v)
        assert VariantModel.get(v.id) is None

    def test_bulk_insert(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        variants = [
            {"variant_name": f"7_{i}", "chromosome": 7, "position": float(i), "alleles": "A/T"}
            for i in range(10)
        ]
        ids = VariantModel.insert_bulk("variant_unique", variants)
        assert len(ids) == 10


class TestGenotypeCRUD:

    def test_create(self, setup_real_db):
        from gemini.db.models.genotypes import GenotypeModel
        g = GenotypeModel.create(genotype_name="GBS_Study_1")
        assert g.genotype_name == "GBS_Study_1"
        assert g.id is not None

    def test_unique_constraint(self, setup_real_db):
        from gemini.db.models.genotypes import GenotypeModel
        GenotypeModel.create(genotype_name="GBS_Study_2")
        dup = GenotypeModel.get_or_create(genotype_name="GBS_Study_2")
        assert len(GenotypeModel.search(genotype_name="GBS_Study_2")) == 1

    def test_update_info(self, setup_real_db):
        from gemini.db.models.genotypes import GenotypeModel
        g = GenotypeModel.create(genotype_name="GBS_Study_3")
        GenotypeModel.update(g, genotype_info={"platform": "GBS", "species": "cowpea"})
        refreshed = GenotypeModel.get(g.id)
        assert refreshed.genotype_info["platform"] == "GBS"


class TestExperimentGenotypeAssociation:

    def test_association(self, setup_real_db):
        from gemini.db.models.experiments import ExperimentModel
        from gemini.db.models.genotypes import GenotypeModel
        from gemini.db.models.associations import ExperimentGenotypeModel

        exp = ExperimentModel.get_or_create(experiment_name="Genomic Exp")
        geno = GenotypeModel.get_or_create(genotype_name="Assoc_Study")
        assoc = ExperimentGenotypeModel.get_or_create(
            experiment_id=exp.id, genotype_id=geno.id
        )
        assert assoc is not None

        found = ExperimentGenotypeModel.get_by_parameters(
            experiment_id=exp.id, genotype_id=geno.id
        )
        assert found is not None


class TestGenotypeRecordCRUD:

    def _create_prereqs(self):
        from gemini.db.models.variants import VariantModel
        from gemini.db.models.genotypes import GenotypeModel
        from gemini.db.models.populations import PopulationModel

        v = VariantModel.get_or_create(
            variant_name="rec_1_100", chromosome=1, position=10.0, alleles="T/C"
        )
        g = GenotypeModel.get_or_create(genotype_name="RecordStudy")
        p = PopulationModel.get_or_create(
            population_accession="IT89KD-288", population_name="IT89KD-288"
        )
        return v, g, p

    def test_bulk_insert(self, setup_real_db):
        from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
        v, g, p = self._create_prereqs()

        records = [
            {
                "genotype_id": str(g.id),
                "genotype_name": g.genotype_name,
                "variant_id": str(v.id),
                "variant_name": v.variant_name,
                "chromosome": v.chromosome,
                "position": v.position,
                "population_id": str(p.id),
                "population_name": p.population_name,
                "population_accession": p.population_accession,
                "call_value": "TT",
                "record_info": {},
            }
        ]
        ids = GenotypeRecordModel.insert_bulk("genotype_records_unique", records)
        assert len(ids) == 1

    def test_unique_constraint(self, setup_real_db):
        from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
        from gemini.db.models.variants import VariantModel
        from gemini.db.models.genotypes import GenotypeModel
        from gemini.db.models.populations import PopulationModel

        v = VariantModel.get_or_create(
            variant_name="uniq_test", chromosome=1, position=5.0, alleles="A/G"
        )
        g = GenotypeModel.get_or_create(genotype_name="UniqStudy")
        p = PopulationModel.get_or_create(
            population_accession="CB27", population_name="CB27"
        )

        record = {
            "genotype_id": str(g.id),
            "genotype_name": g.genotype_name,
            "variant_id": str(v.id),
            "variant_name": v.variant_name,
            "chromosome": 1,
            "position": 5.0,
            "population_id": str(p.id),
            "population_name": "CB27",
            "population_accession": "CB27",
            "call_value": "AA",
            "record_info": {},
        }
        ids1 = GenotypeRecordModel.insert_bulk("genotype_records_unique", [record])
        # Inserting the same record again should not duplicate
        ids2 = GenotypeRecordModel.insert_bulk("genotype_records_unique", [record])
        all_records = GenotypeRecordModel.search(
            genotype_name="UniqStudy", variant_name="uniq_test", population_name="CB27"
        )
        assert len(all_records) == 1


class TestGenotypeRecordBulkWithFixture:
    """Test bulk insert using the test fixture data."""

    def test_fixture_bulk_load(self, setup_real_db):
        from gemini.db.models.variants import VariantModel
        from gemini.db.models.genotypes import GenotypeModel
        from gemini.db.models.populations import PopulationModel
        from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
        from tests.fixtures.genomic_data import (
            FIXTURE_VARIANTS,
            FIXTURE_POPULATIONS,
            FIXTURE_GENOTYPE,
            FIXTURE_GENOTYPE_CALLS,
        )

        # Create variants
        variant_ids = VariantModel.insert_bulk("variant_unique", FIXTURE_VARIANTS)
        assert len(variant_ids) == 50

        # Create populations
        for pop in FIXTURE_POPULATIONS:
            PopulationModel.get_or_create(**pop)

        # Create genotype study
        geno = GenotypeModel.get_or_create(**FIXTURE_GENOTYPE)
        assert geno is not None

        # Build lookup maps
        variant_map = {}
        for v in FIXTURE_VARIANTS:
            db_v = VariantModel.get_by_parameters(variant_name=v["variant_name"])
            variant_map[v["variant_name"]] = db_v

        pop_map = {}
        for p in FIXTURE_POPULATIONS:
            db_p = PopulationModel.get_by_parameters(
                population_name=p["population_name"],
                population_accession=p["population_accession"],
            )
            pop_map[p["population_name"]] = db_p

        # Build genotype records
        records = []
        for call in FIXTURE_GENOTYPE_CALLS:
            v = variant_map[call["variant_name"]]
            p = pop_map[call["population_name"]]
            records.append({
                "genotype_id": str(geno.id),
                "genotype_name": geno.genotype_name,
                "variant_id": str(v.id),
                "variant_name": v.variant_name,
                "chromosome": v.chromosome,
                "position": v.position,
                "population_id": str(p.id),
                "population_name": p.population_name,
                "population_accession": p.population_accession,
                "call_value": call["call_value"],
                "record_info": {},
            })

        ids = GenotypeRecordModel.insert_bulk("genotype_records_unique", records)
        assert len(ids) == 500

    def test_export_hapmap_from_fixture(self, setup_real_db):
        """Load fixture data and export as HapMap to verify end-to-end."""
        from gemini.db.models.variants import VariantModel
        from gemini.db.models.genotypes import GenotypeModel
        from gemini.db.models.populations import PopulationModel
        from gemini.db.models.columnar.genotype_records import GenotypeRecordModel
        from gemini.api.genotype import Genotype
        from tests.fixtures.genomic_data import (
            FIXTURE_VARIANTS,
            FIXTURE_POPULATIONS,
            FIXTURE_GENOTYPE,
            FIXTURE_GENOTYPE_CALLS,
        )

        # Load data
        VariantModel.insert_bulk("variant_unique", FIXTURE_VARIANTS)
        for pop in FIXTURE_POPULATIONS:
            PopulationModel.get_or_create(**pop)
        geno = GenotypeModel.get_or_create(**FIXTURE_GENOTYPE)

        variant_map = {}
        for v in FIXTURE_VARIANTS:
            db_v = VariantModel.get_by_parameters(variant_name=v["variant_name"])
            variant_map[v["variant_name"]] = db_v

        pop_map = {}
        for p in FIXTURE_POPULATIONS:
            db_p = PopulationModel.get_by_parameters(
                population_name=p["population_name"],
                population_accession=p["population_accession"],
            )
            pop_map[p["population_name"]] = db_p

        records = []
        for call in FIXTURE_GENOTYPE_CALLS:
            v = variant_map[call["variant_name"]]
            p = pop_map[call["population_name"]]
            records.append({
                "genotype_id": str(geno.id),
                "genotype_name": geno.genotype_name,
                "variant_id": str(v.id),
                "variant_name": v.variant_name,
                "chromosome": v.chromosome,
                "position": v.position,
                "population_id": str(p.id),
                "population_name": p.population_name,
                "population_accession": p.population_accession,
                "call_value": call["call_value"],
                "record_info": {},
            })
        GenotypeRecordModel.insert_bulk("genotype_records_unique", records)

        # Export
        genotype_api = Genotype(genotype_name=geno.genotype_name, id=geno.id)
        hapmap = genotype_api.export(format="hapmap")

        lines = hapmap.strip().split("\n")
        header = lines[0].split("\t")

        # Validate HapMap structure
        assert header[0] == "rs#"
        assert header[1] == "alleles"
        assert header[2] == "chrom"
        assert len(lines) == 51  # 1 header + 50 variants

        # Check sample names are present
        for pop in FIXTURE_POPULATIONS:
            assert pop["population_name"] in header
