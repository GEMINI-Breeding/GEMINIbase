# Model Experiment API Example

This example demonstrates how to associate and unassociate experiments with models using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/model_experiment_api.py`.

## Code

```python
from gemini.api.model import Model

# Create a new model for Experiment A
new_model = Model.create(
    model_name="Model Test 1",
    model_url="https://example.com/model_test_1",
    model_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Model: {new_model}")

# Get associated experiments
associated_experiments = new_model.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the model with Experiment B
new_model.associate_experiment(experiment_name="Experiment B")
print(f"Associated Model with Experiment B")

# Check if the model is associated with Experiment B
is_associated = new_model.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Model associated with Experiment B? {is_associated}")

# Unassociate the model from Experiment B
new_model.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Model from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_model.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Model still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between experiments and models:

*   **Creating a model:** The `Model.create()` method is used to create a new model with a name, URL, additional information, and associated experiment.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the model.
*   **Associating with an experiment:** The `associate_experiment()` method associates the model with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the model is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the model and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the model is no longer associated with Experiment B.
