from gemini.api.population import Population

new_population = Population.create(
    population_name="Population Test 1",
    population_type="diversity_panel",
    species="Zea mays",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created Population: {new_population}")

population = Population.get("Population Test 1")
print(f"Got Population: {population}")

population_by_id = Population.get_by_id(new_population.id)
print(f"Got Population by ID: {population_by_id}")

all_populations = Population.get_all()
print(f"All Populations:")
for population in all_populations:
    print(population)

searched_populations = Population.search(experiment_name="Experiment A")
length_searched_populations = len(searched_populations)
print(f"Found {length_searched_populations} populations in Experiment A")

population.refresh()
print(f"Refreshed Population: {population}")

population.set_info(population_info={"test": "test_updated"})
print(f"Updated Population Info: {population.get_info()}")

exists = Population.exists(population_name="Population Test 1")
print(f"Population exists: {exists}")

is_deleted = new_population.delete()
print(f"Deleted Population: {is_deleted}")

exists_after_deletion = Population.exists(population_name="Population Test 1")
print(f"Population exists after deletion: {exists_after_deletion}")
