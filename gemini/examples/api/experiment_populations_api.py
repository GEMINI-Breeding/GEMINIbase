from gemini.api.experiment import Experiment
from gemini.api.population import Population

new_population = Population.create(
    population_name="New Population",
    population_type="ril",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)

experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

experiment_b.associate_population(population_name=new_population.population_name)

associated_populations = experiment_b.get_associated_populations()
for population in associated_populations:
    print(f"Associated Population: {population}")

is_associated = experiment_b.belongs_to_population(population_name=new_population.population_name)
print(f"Is New Population associated with Experiment B? {is_associated}")

experiment_b.unassociate_population(population_name=new_population.population_name)

is_associated = experiment_b.belongs_to_population(population_name=new_population.population_name)
print(f"Is New Population still associated with Experiment B? {is_associated}")

experiment_population = experiment_b.create_new_population(
    population_name="Experiment B Population",
    population_type="breeding_pop",
    population_info={"test": "test"}
)
print(f"Created New Population: {experiment_population}")
