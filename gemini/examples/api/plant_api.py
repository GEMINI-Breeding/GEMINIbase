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