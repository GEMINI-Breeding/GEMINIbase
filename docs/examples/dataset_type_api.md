# Dataset Type API Example

This example demonstrates how to use the DatasetType API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/dataset_type_api.py`.

## Code

```python
from gemini.api.dataset_type import DatasetType

# Create a new dataset type
new_dataset_type = DatasetType.create(
    dataset_type_name="Test Dataset Type",
    dataset_type_info={
        "description": "This is a test dataset type for API demonstration.",
        "version": "1.0",
    }
)
print(f"Created new dataset type: {new_dataset_type}")

# Get Dataset Type by ID
dataset_type_by_id = DatasetType.get_by_id(new_dataset_type.id)
print(f"Dataset Type by ID: {dataset_type_by_id}")

# Get Dataset Type by Name
dataset_type_by_name = DatasetType.get(dataset_type_name="Test Dataset Type")
print(f"Dataset Type by Name: {dataset_type_by_name}")

# Get all Dataset Types
all_dataset_types = DatasetType.get_all()
for dataset_type in all_dataset_types:
    print(dataset_type)

# Search Dataset Types
search_results = DatasetType.search(dataset_type_name="Test Dataset Type")
for result in search_results:
    print(f"Search Result: {result}")

# Update Dataset Type
dataset_type = dataset_type.update(
    dataset_type_info={
        "description": "Updated test dataset type for API demonstration.",
        "version": "1.1",
    }
)
print(f"Updated Dataset Type: {dataset_type}")

# Set Dataset Type Info
dataset_type.set_info(
    dataset_type_info={
        "description": "New test dataset type for API demonstration.",
        "version": "2.0",
    }
)
print(f"Dataset Type Info set: {dataset_type.get_info()}")

# Check if Dataset Type exists
dataset_type_exists = DatasetType.exists(dataset_type_name="Test Dataset Type")
print(f"Does Dataset Type exist? {dataset_type_exists}")

# Delete Dataset Type
dataset_type.delete()
print(f"Dataset Type deleted: {dataset_type}")

# Check if Dataset Type exists after deletion
dataset_type_exists_after_deletion = DatasetType.exists(dataset_type_name="Test Dataset Type")
print(f"Does Dataset Type exist after deletion? {dataset_type_exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing dataset types using the GEMINIbase API:

*   **Creating a dataset type:** The `DatasetType.create()` method is used to create a new dataset type with a name and additional information (description, version).
*   **Getting a dataset type:** The `DatasetType.get_by_id()` method retrieves a dataset type by its unique ID. The `DatasetType.get()` method retrieves a dataset type by its name.
*   **Getting all dataset types:** The `DatasetType.get_all()` method retrieves all dataset types in the database.
*   **Searching for dataset types:** The `DatasetType.search()` method finds dataset types based on specified criteria, such as the name.
*   **Updating a dataset type:** The `DatasetType.update()` method updates the attributes of an existing dataset type.
*   **Setting dataset type information:** The `DatasetType.set_info()` method updates the `dataset_type_info` field with new data.
*   **Checking for existence:** The `DatasetType.exists()` method verifies if a dataset type with the given name exists.
*   **Deleting a dataset type:** The `DatasetType.delete()` method removes the dataset type from the database.
