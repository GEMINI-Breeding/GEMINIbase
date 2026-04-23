# Trait Experiment API Example

This example demonstrates how to associate and unassociate experiments with traits using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/trait_experiment_api.py`.

## Code

```python
from gemini.api.trait import Trait

# Create a new Trait for Experiment A
new_trait = Trait.create(
    trait_name="Trait X",
    trait_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Trait: {new_trait}")

# Get Associated Experiments
associated_experiments = new_trait.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the new trait with Experiment B
new_trait.associate_experiment(experiment_name="Experiment B")
print(f"Associated Trait with Experiment B")

# Check if the new trait is associated with Experiment B
is_associated = new_trait.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Trait associated with Experiment B? {is_associated}")

# Unassociate the new trait from Experiment B
new_trait.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Trait from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_trait.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Trait still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between experiments and traits:

*   **Creating a trait:** The `Trait.create()` method is used to create a new trait with a name and additional information.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the trait.
*   **Associating with an experiment:** The `associate_experiment()` method associates the trait with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the trait is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the trait and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the trait is no longer associated with Experiment B.
