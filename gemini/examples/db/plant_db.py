from gemini.db.models.plants import PlantModel

# Get All Plants
plants = PlantModel.all()

# Print Plants
print("Plants:")
for plant in plants:
    print(f"{plant.id}: {plant.plant_number}")

    # Print Population
    print(f"Population: {plant.population.population_accession} {plant.population.population_name}")


