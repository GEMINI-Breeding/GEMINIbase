# Experiment Populations API Example

This example demonstrates how to associate and unassociate populations with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_populations_api.py`.

## Code

```python
from gemini.api.experiment import Experiment
from gemini.api.population import Population

# Create a new population for Experiment A
new_population = Population.create(
    population_name="New Population",
    population_type="breeding",
    species="Triticum aestivum",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new population
experiment_b.associate_population(
    population_name=new_population.population_name
)

# Get Associated Populations
associated_populations = experiment_b.get_associated_populations()
for population in associated_populations:
    print(f"Associated Population: {population}")

# Check if the new population is associated with Experiment B
is_associated = experiment_b.belongs_to_population(
    population_name=new_population.population_name
)
print(f"Is New Population associated with Experiment B? {is_associated}")

# Unassociate the new population from Experiment B
experiment_b.unassociate_population(
    population_name=new_population.population_name
)

# Check if the new population is still associated with Experiment B
is_associated = experiment_b.belongs_to_population(
    population_name=new_population.population_name
)
print(f"Is New Population still associated with Experiment B? {is_associated}")

# Create a new population for Experiment B
experiment_population = experiment_b.create_new_population(
    population_name="Experiment B Population",
    population_type="breeding",
    species="Triticum aestivum",
    population_info={"test": "test"}
)
print(f"Created New Population: {experiment_population}")
```

## Explanation

This example demonstrates how to manage the association between populations and experiments:

*   **Creating a population:** A new population is created and associated with Experiment A.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment B in this case).
*   **Associating with a population:** The `associate_population()` method associates the experiment with the created population.
*   **Getting associated populations:** The `get_associated_populations()` method retrieves a list of populations associated with the experiment.
*   **Checking association:** The `belongs_to_population()` method verifies if the experiment is associated with a specific population.
*   **Unassociating from a population:** The `unassociate_population()` method removes the association between the experiment and the population.
*   **Verifying unassociation:** The `belongs_to_population()` method is used again to confirm that the experiment is no longer associated with the population.
*   **Creating a new population for an experiment:** The `create_new_population()` method creates a new population and automatically associates it with the experiment.
