# Plant API Example

This example demonstrates how to use the Plant API in the Gemini framework.

## Source File Location

The original Python script is located at `gemini/examples/api/plant_api.py`.

## Code

```python
from gemini.api.plant import Plant

# Create a new plant
new_plant = Plant.create(
    plant_number=1000,
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1,
    plant_info={"test": "test"},
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1",
    population_accession="Accession A1",
    population_name="Population A"
)
print(f"Created New Plant: {new_plant}")

# Get Plant by ID
plant_by_id = Plant.get_by_id(new_plant.id)
print(f"Got Plant by ID: {plant_by_id}")

# Get Plant
plant = Plant.get(
    plant_number=new_plant.plant_number,
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Got Plant: {plant}")

# Get all plants
all_plants = Plant.get_all()
print(f"All Plants:")
for p in all_plants[:10]:  # Limit to first 10 plants for display
    print(p)

# Search for plants in Experiment A
searched_plants = Plant.search(experiment_name="Experiment A")
length_searched_plants = len(searched_plants)
print(f"Found {length_searched_plants} plants in Experiment A")

# Refresh the plant
new_plant.refresh()
print(f"Refreshed Plant: {new_plant}")

# Update the plant
new_plant.update(
    plant_number=2000,
    plant_info={"updated": "info"},
)
print(f"Updated Plant: {new_plant}")

# Set Plant Info
new_plant.set_info(plant_info={"new": "info"})
print(f"Set Plant Info: {new_plant.get_info()}")

# Check if the plant exists
exists = Plant.exists(
    plant_number=new_plant.plant_number,
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Does the plant exist? {exists}")

# Delete the plant
is_deleted = new_plant.delete()
print(f"Deleted Plant: {is_deleted}")

# Check if the plant was deleted
exists_after_deletion = Plant.exists(
    plant_number=2000,
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Does the plant exist after deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing plants using the Gemini API:

*   **Creating a plant:** The `Plant.create()` method is used to create a new plant with a plant number, plot information, additional information, and associated experiment, season, site, and population.
*   **Getting a plant:** The `Plant.get_by_id()` method retrieves a plant by its unique ID. The `Plant.get()` method retrieves a plant by its plant number, plot information, and associated experiment, season, and site.
*   **Getting all plants:** The `Plant.get_all()` method retrieves all plants in the database.
*   **Searching for plants:** The `Plant.search()` method finds plants based on specified criteria, such as the experiment name.
*   **Refreshing a plant:** The `Plant.refresh()` method updates the plant object with the latest data from the database.
*   **Updating a plant:** The `Plant.update()` method updates the attributes of an existing plant.
*   **Setting plant information:** The `Plant.set_info()` method updates the `plant_info` field with new data.
*   **Checking for existence:** The `Plant.exists()` method verifies if a plant with the given attributes exists.
*   **Deleting a plant:** The `Plant.delete()` method removes the plant from the database.
