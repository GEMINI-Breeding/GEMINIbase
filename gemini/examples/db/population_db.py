from gemini.db.models.populations import PopulationModel

# Get all populations
populations = PopulationModel.all()

# Get population by id
population = PopulationModel.get(1)

# Get population by parameters
population = PopulationModel.get_by_parameters(
    population_name="Default",
    population_accession="Default"
)

