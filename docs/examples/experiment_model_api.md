# Experiment Model API Example

This example demonstrates how to associate and unassociate models with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_model_api.py`.

## Code

```python
from gemini.api.experiment import Experiment
from gemini.api.model import Model

# Create a new model for Experiment A
new_model = Model.create(
    model_name="New Model",
    model_url="gs://gemini-models/new_model.pkl",
    model_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Model: {new_model}")

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new model
experiment_b.associate_model(model_name=new_model.model_name)
print(f"Associated New Model with Experiment B: {experiment_b}")

# Get Associated Models
associated_models = experiment_b.get_associated_models()
for model in associated_models:
    print(f"Associated Model: {model}")

# Check if the new model is associated with Experiment B
is_associated = experiment_b.belongs_to_model(model_name=new_model.model_name)
print(f"Is New Model associated with Experiment B? {is_associated}")

# Unassociate the new model from Experiment B
experiment_b.unassociate_model(model_name=new_model.model_name)
print(f"Unassociated New Model from Experiment B: {experiment_b}")

# Check if the new model is still associated with Experiment B
is_associated = experiment_b.belongs_to_model(model_name=new_model.model_name)
print(f"Is New Model still associated with Experiment B? {is_associated}")

# Create a new model for Experiment B
experiment_model = experiment_b.create_new_model(
    model_name="Experiment B Model",
    model_url="gs://gemini-models/experiment_b_model.pkl",
    model_info={"test": "test"}
)
print(f"Created New Model: {experiment_model}")
```

## Explanation

This example demonstrates how to manage the association between models and experiments:

*   **Creating a model:** A new model is created and associated with Experiment A.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment B in this case).
*   **Associating with a model:** The `associate_model()` method associates the experiment with the created model.
*   **Getting associated models:** The `get_associated_models()` method retrieves a list of models associated with the experiment.
*   **Checking association:** The `belongs_to_model()` method verifies if the experiment is associated with a specific model.
*   **Unassociating from a model:** The `unassociate_model()` method removes the association between the experiment and the model.
*   **Verifying unassociation:** The `belongs_to_model()` method is used again to confirm that the experiment is no longer associated with the model.
*   **Creating a new model for an experiment:** The `create_new_model()` method creates a new model and automatically associates it with the experiment.
