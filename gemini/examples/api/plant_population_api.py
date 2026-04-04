from gemini.api.plant import Plant
from gemini.api.population import Population

# Create a new Plant
new_plant = Plant.create(
    plant_number=4444,
    plant_info={
        "test": "test"
    }
)
print(f"Created New Plant: {new_plant}")

# Create a new Population
new_population = Population.create(
    population_name="Population Test 1",
    population_accession="Accession A",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Population: {new_population}")

# Associate the plant with the population
new_plant.associate_population(
    population_name="Population Test 1",
    population_accession="Accession A"
)
print(f"Associated Plant with Population: {new_plant}")

# Check if the plant is associated with the population
is_associated_population = new_plant.belongs_to_population(
    population_name="Population Test 1",
    population_accession="Accession A"
)
print(f"Is Plant associated with Population: {is_associated_population}")

# Unassociate the plant from the population
new_plant.unassociate_population()
print(f"Unassociated Plant from Population: {new_plant}")

# Check if the plant is unassociated from the population
is_unassociated_population = new_plant.belongs_to_population(
    population_name="Population Test 1",
    population_accession="Accession A"
)
print(f"Is Plant associated with population: {is_unassociated_population}")