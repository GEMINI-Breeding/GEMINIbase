# Plant Population API Example

This example demonstrates how to associate and unassociate populations with plants using the Gemini framework.

## Source File Location

The original Python script is located at `gemini/examples/api/plant_population_api.py`.

## Code

```python
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
```

## Explanation

This example demonstrates how to manage the association between populations and plants:

*   **Creating a plant:** The `Plant.create()` method is used to create a new plant with a plant number and additional information.
*   **Creating a population:** The `Population.create()` method is used to create a new population with a population, accession, additional information, and associated experiment.
*   **Associating with a population:** The `associate_population()` method associates the plant with the created population.
*   **Checking association:** The `belongs_to_population()` method verifies if the plant is associated with a specific population.
*   **Unassociating from a population:** The `unassociate_population()` method removes the association between the plant and the population.
*   **Verifying unassociation:** The `belongs_to_population()` method is used again to confirm that the plant is no longer associated with the population.
