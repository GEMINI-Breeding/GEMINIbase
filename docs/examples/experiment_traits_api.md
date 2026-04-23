# Experiment Traits API Example

This example demonstrates how to associate and unassociate traits with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_traits_api.py`.

## Code

```python
from gemini.api.experiment import Experiment
from gemini.api.trait import Trait

# Create a new trait for Experiment A
new_trait = Trait.create(
    trait_name="New Trait",
    trait_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Trait: {new_trait}")

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new trait
experiment_b.associate_trait(trait_name=new_trait.trait_name)
print(f"Associated New Trait with Experiment B: {experiment_b}")

# Get Associated Traits
associated_traits = experiment_b.get_associated_traits()
for trait in associated_traits:
    print(f"Associated Trait: {trait}")

# Check if the new trait is associated with Experiment B
is_associated = experiment_b.belongs_to_trait(trait_name=new_trait.trait_name)
print(f"Is New Trait associated with Experiment B? {is_associated}")

# Unassociate the new trait from Experiment B
experiment_b.unassociate_trait(trait_name=new_trait.trait_name)
print(f"Unassociated New Trait from Experiment B: {experiment_b}")

# Check if the new trait is still associated with Experiment B
is_associated = experiment_b.belongs_to_trait(trait_name=new_trait.trait_name)
print(f"Is New Trait still associated with Experiment B? {is_associated}")

# Create a new trait for Experiment B
experiment_trait = experiment_b.create_new_trait(
    trait_name="Experiment B Trait",
    trait_info={"test": "test"}
)
print(f"Created New Trait: {experiment_trait}")
```

## Explanation

This example demonstrates how to manage the association between traits and experiments:

*   **Creating a trait:** A new trait is created and associated with Experiment A.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment B in this case).
*   **Associating with a trait:** The `associate_trait()` method associates the experiment with the created trait.
*   **Getting associated traits:** The `get_associated_traits()` method retrieves a list of traits associated with the experiment.
*   **Checking association:** The `belongs_to_trait()` method verifies if the experiment is associated with a specific trait.
*   **Unassociating from a trait:** The `unassociate_trait()` method removes the association between the experiment and the trait.
*   **Verifying unassociation:** The `belongs_to_trait()` method is used again to confirm that the experiment is no longer associated with the trait.
*   **Creating a new trait for an experiment:** The `create_new_trait()` method creates a new trait and automatically associates it with the experiment.
