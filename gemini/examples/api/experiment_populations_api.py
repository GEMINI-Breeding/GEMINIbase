from gemini.api.experiment import Experiment
from gemini.api.population import Population

# Create a new population for Experiment A
new_population = Population.create(
    population_accession="New Population",
    population_name="New Population",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new population
experiment_b.associate_population(
    population_accession=new_population.population_accession,
    population_name=new_population.population_name
)

# Get Associated Populations
associated_populations = experiment_b.get_associated_populations()
for population in associated_populations:
    print(f"Associated Population: {population}")

# Check if the new population is associated with Experiment B
is_associated = experiment_b.belongs_to_population(
    population_accession=new_population.population_accession,
    population_name=new_population.population_name
)
print(f"Is New Population associated with Experiment B? {is_associated}")

# Unassociate the new population from Experiment B
experiment_b.unassociate_population(
    population_accession=new_population.population_accession,
    population_name=new_population.population_name
)

# Check if the new population is still associated with Experiment B
is_associated = experiment_b.belongs_to_population(
    population_accession=new_population.population_accession,
    population_name=new_population.population_name
)
print(f"Is New Population still associated with Experiment B? {is_associated}")

# Create a new population for Experiment B
experiment_population = experiment_b.create_new_population(
    population_accession="Experiment B Population",
    population_name="Experiment B Population",
    population_info={"test": "test"}
)
print(f"Created New Population: {experiment_population}")
