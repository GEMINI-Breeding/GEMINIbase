# Population Experiment API Example

This example demonstrates how to associate and unassociate populations with experiments using the Gemini framework.

## Source File Location

The original Python script is located at `gemini/examples/api/population_experiment_api.py`.

## Code

```python
from gemini.api.population import Population

# Create a new population for Experiment A
new_population = Population.create(
    population_name="Population Test 1",
    population_type="breeding",
    species="Triticum aestivum",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created Population: {new_population}")

# Get Associated Experiments
associated_experiments = new_population.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the population with Experiment B
new_population.associate_experiment(experiment_name="Experiment B")
print(f"Associated Population with Experiment B")

# Check if the population is associated with Experiment B
is_associated = new_population.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Population associated with Experiment B? {is_associated}")

# Unassociate the population from Experiment B
new_population.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Population from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_population.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Population still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between populations and experiments:

*   **Creating a population:** A new population is created and associated with Experiment A.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the population.
*   **Associating with an experiment:** The `associate_experiment()` method associates the population with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the population is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the population and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the population is no longer associated with Experiment B.
