from gemini.db.models.populations import PopulationModel

populations = PopulationModel.all()

population = PopulationModel.get(1)

population = PopulationModel.get_by_parameters(
    population_name="Population A"
)
