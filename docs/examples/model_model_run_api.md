# Model Model Run API Example

This example demonstrates how to use the Model and ModelRun APIs to associate model runs with models in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/model_model_run_api.py`.

## Code

```python
from gemini.api.model import Model

# Get Model A
model_a = Model.get("Model A")
print(f"Got Model A: {model_a}")

# Create a new model run for Model A
new_model_a_run = model_a.create_new_run(
    model_run_info={"test": "test"}
)

# Get Associated Model Runs
associated_model_runs = model_a.get_associated_runs()
for model_run in associated_model_runs:
    print(f"Associated Model Run: {model_run}")
```

## Explanation

This example demonstrates how to manage the association between model runs and models:

*   **Getting a model:** The `Model.get()` method retrieves a model by its name (Model A in this case).
*   **Creating a new model run:** The `create_new_run()` method creates a new model run and automatically associates it with the model.
*   **Getting associated model runs:** The `get_associated_runs()` method retrieves a list of model runs associated with the model.
