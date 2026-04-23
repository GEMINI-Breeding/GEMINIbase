# Model Run API Example

This example demonstrates how to use the ModelRun API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/model_run_api.py`.

## Code

```python
from gemini.api.model_run import ModelRun
from gemini.api.model import Model

# Create a new model run for Model A
new_model_run = ModelRun.create(
    model_run_info={"test": "test"},
    model_name="Model A"
)
print(f"Created New Model Run: {new_model_run}")

# Get Model Run by ID
model_run_b = ModelRun.get(new_model_run.id)
print(f"Got Model Run B: {model_run_b}")

# Get Model Run by Model Name and Model Info
model_run_b = ModelRun.get(
    model_name="Model A",
    model_run_info={"test": "test"}
)
print(f"Got Model Run B: {model_run_b}")

# Get all model runs
all_model_runs = ModelRun.get_all()
print(f"All Model Runs: {all_model_runs}")

# Search for model runs by name
search_results = ModelRun.search(model_name="Model A")
for result in search_results:
    print(f"Search Result: {result}")

# Update Model Run
model_run_b.update(model_run_info={"updated": "info"})
print(f"Updated Model Run B: {model_run_b}")

# Set Model Run Info
model_run_b.set_info(
    model_run_info={"new": "info"}
)
print(f"Set Model Run Info: {model_run_b.get_info()}")

# Refresh Model Run
model_run_b.refresh()
print(f"Refreshed Model Run B: {model_run_b}")

# Check if Model Run Exists
exists = ModelRun.exists(
    model_name="Model A",
    model_run_info={"new": "info"}
)
print(f"Does Model Run Exist? {exists}")

# Delete Model Run
is_deleted = model_run_b.delete()
print(f"Deleted Model Run B: {is_deleted}")

# Check if Model Run Exists after Deletion
exists = ModelRun.exists(
    model_name="Model A",
    model_run_info={"new": "info"}
)
print(f"Does Model Run Exist after Deletion? {exists}")
```

## Explanation

This example demonstrates the basic operations for managing model runs using the GEMINIbase API:

*   **Creating a model run:** The `ModelRun.create()` method is used to create a new model run with additional information and associated model.
*   **Getting a model run:** The `ModelRun.get()` method retrieves a model run by its ID or model name and model run info.
*   **Getting all model runs:** The `ModelRun.get_all()` method retrieves all model runs in the database.
*   **Searching for model runs:** The `ModelRun.search()` method finds model runs based on specified criteria, such as the model name.
*   **Updating a model run:** The `ModelRun.update()` method updates the attributes of an existing model run.
*   **Setting model run information:** The `ModelRun.set_info()` method updates the `model_run_info` field with new data.
*   **Refreshing a model run:** The `ModelRun.refresh()` method updates the model run object with the latest data from the database.
*   **Checking for existence:** The `ModelRun.exists()` method verifies if a model run with the given attributes exists.
*   **Deleting a model run:** The `ModelRun.delete()` method removes the model run from the database.
