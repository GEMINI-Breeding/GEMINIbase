# Model API Example

This example demonstrates how to use the Model API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/model_api.py`.

## Code

```python
from gemini.api.model import Model

# Create a new model for Experiment A
new_model = Model.create(
    model_name="Model A",
    model_url="https://example.com/model_a",
    model_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Model: {new_model}")

# Get Model by ID
model_from_id = Model.get(new_model.id)
print(f"Got Model from ID: {model_from_id}")

# Get Model by Name
model_from_name = Model.get(model_name="Model A")
print(f"Got Model from Name: {model_from_name}")

# Get all models
all_models = Model.get_all()
for model in all_models:
    print(f"Model: {model}")

# Search for models by name
search_results = Model.search(model_name="Model A")
for result in search_results:
    print(f"Search Result: {result}")

# Update Model
model_from_name.update(
    model_url="https://example.com/updated_model_a",
    model_info={"updated": "info"}
)
print(f"Updated Model: {model_from_name}")

# Refresh Model
model_from_name.refresh()
print(f"Refreshed Model: {model_from_name}")

# Set Model Info
model_from_name.set_info(
    model_info={"new": "info"}
)
print(f"Set Model Info: {model_from_name.get_info()}")

# Check if Model Exists
exists = Model.exists(model_name="Model A")
print(f"Does Model Exist? {exists}")

# Delete Model
is_deleted = model_from_name.delete()
print(f"Deleted Model: {is_deleted}")

# Check if Model Exists after Deletion
exists = Model.exists(model_name="Model A")
print(f"Does Model Exist after Deletion? {exists}")
```

## Explanation

This example demonstrates the basic operations for managing models using the GEMINIbase API:

*   **Creating a model:** The `Model.create()` method is used to create a new model with a name, URL, additional information, and associated experiment.
*   **Getting a model:** The `Model.get()` method retrieves a model by its ID or name.
*   **Getting all models:** The `Model.get_all()` method retrieves all models in the database.
*   **Searching for models:** The `Model.search()` method finds models based on specified criteria, such as the name.
*   **Updating a model:** The `Model.update()` method updates the attributes of an existing model.
*   **Refreshing a model:** The `Model.refresh()` method updates the model object with the latest data from the database.
*   **Setting model information:** The `Model.set_info()` method updates the `model_info` field with new data.
*   **Checking for existence:** The `Model.exists()` method verifies if a model with the given name exists.
*   **Deleting a model:** The `Model.delete()` method removes the model from the database.
