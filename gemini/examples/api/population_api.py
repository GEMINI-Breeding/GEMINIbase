from gemini.api.population import Population

# Create a new Population for Experiment A
new_population = Population.create(
    population_name="Population Test 1",
    population_accession="Accession A",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created Population: {new_population}")

# Get Population with Population and Accession
population = Population.get("Population Test 1", "Accession A")
print(f"Got Population: {population}")

# Get the same Population by ID
population_by_id = Population.get_by_id(new_population.id)
print(f"Got Population by ID: {population_by_id}")

# Get all populations
all_populations = Population.get_all()
print(f"All Populations:")
for population in all_populations:
    print(population)

# Search for populations in Experiment A
searched_populations = Population.search(experiment_name="Experiment A")
length_searched_populations = len(searched_populations)
print(f"Found {length_searched_populations} populations in Experiment A")

# Refresh the population
population.refresh()
print(f"Refreshed Population: {population}")

# Update the population_info
population.set_info(
    population_info={"test": "test_updated"},
)
print(f"Updated Population Info: {population.get_info()}")

# Check if the population exists before deletion
exists = Population.exists(
    population_name="Population Test 1",
    population_accession="Accession A"
)
print(f"Population exists: {exists}")

# Delete the created population
is_deleted = new_population.delete()
print(f"Deleted Population: {is_deleted}")

# Check if the population exists after deletion
exists_after_deletion = Population.exists(
    population_name="Population Test 1",
    population_accession="Accession A"
)
print(f"Population exists after deletion: {exists_after_deletion}")
