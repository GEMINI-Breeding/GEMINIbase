"""Tests for the Population API class Pydantic model and validation."""

import pytest
from uuid import uuid4
from gemini.api.population import Population


class TestPopulationModel:

    def test_construct_with_required_fields(self):
        pop = Population(population_name="Maize Diversity Panel")
        assert pop.population_name == "Maize Diversity Panel"
        assert pop.id is None
        assert pop.population_type is None
        assert pop.species is None
        assert pop.population_info is None

    def test_construct_with_all_fields(self):
        uid = uuid4()
        pop = Population(
            id=uid,
            population_name="Bean RIL Pop",
            population_type="ril",
            species="Phaseolus vulgaris",
            population_info={"size": 200},
        )
        assert pop.id == uid
        assert pop.population_name == "Bean RIL Pop"
        assert pop.population_type == "ril"
        assert pop.species == "Phaseolus vulgaris"
        assert pop.population_info == {"size": 200}

    def test_id_alias_population_id(self):
        uid = uuid4()
        pop = Population.model_validate({"population_id": str(uid), "population_name": "X"})
        assert str(pop.id) == str(uid)

    def test_population_name_is_required(self):
        with pytest.raises(Exception):
            Population.model_validate({})

    def test_no_population_accession_field(self):
        pop = Population(population_name="Test")
        assert not hasattr(pop, "population_accession")

    def test_str_representation(self):
        pop = Population(population_name="Maize Panel")
        assert "Maize Panel" in str(pop)
