# Population API Example

This example demonstrates how to use the Population API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/population_api.py`.

## Code

```python
from gemini.api.population import Population

# Create a new Population for Experiment A
new_population = Population.create(
    population_name="Population Test 1",
    population_type="breeding",
    species="Triticum aestivum",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created Population: {new_population}")

# Get Population by name
population = Population.get("Population Test 1")
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
    population_name="Population Test 1"
)
print(f"Population exists: {exists}")

# Delete the created population
is_deleted = new_population.delete()
print(f"Deleted Population: {is_deleted}")

# Check if the population exists after deletion
exists_after_deletion = Population.exists(
    population_name="Population Test 1"
)
print(f"Population exists after deletion: {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing populations using the GEMINIbase API:

*   **Creating a population:**  The `Population.create()` method is used to create a new population associated with a specific experiment.
*   **Getting a population:** The `Population.get()` method retrieves a population by its name.  The `Population.get_by_id()` method retrieves a population by its unique ID.
*   **Getting all populations:** The `Population.get_all()` method retrieves all populations in the database.
*   **Searching for populations:** The `Population.search()` method finds populations based on specified criteria, such as the experiment name.
*   **Refreshing a population:** The `Population.refresh()` method updates the population object with the latest data from the database.
*   **Updating population information:** The `Population.set_info()` method updates the `population_info` field with new data.
*   **Checking for existence:** The `Population.exists()` method verifies if a population with the given name exists.
*   **Deleting a population:** The `Population.delete()` method removes the population from the database.
