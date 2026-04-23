# Data Type API Example

This example demonstrates how to use the Data Type API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/data_type_api.py`.

## Code

```python
from gemini.api.data_type import DataType

# Create a new data type
new_data_type = DataType.create(
    data_type_name="Test Data Type",
    data_type_info={
        "description": "This is a test data type for API demonstration.",
        "version": "1.0",
    }
)
print(f"Created new data type: {new_data_type}")

# Get Data Type by ID
data_type_by_id = DataType.get_by_id(new_data_type.id)
print(f"Data Type by ID: {data_type_by_id}")

# Get Data Type by Name
data_type_by_name = DataType.get(data_type_name="Test Data Type")
print(f"Data Type by Name: {data_type_by_name}")

# Get all Data Types
all_data_types = DataType.get_all()
for data_type in all_data_types:
    print(data_type)

# Search Data Types
search_results = DataType.search(data_type_name="Test Data Type")
for result in search_results:
    print(f"Search Result: {result}")

# Update Data Type
data_type = data_type.update(
    data_type_info={
        "description": "Updated test data type for API demonstration.",
        "version": "1.1",
    }
)
print(f"Updated Data Type: {data_type}")

# Set Data Type Info
data_type.set_info(
    data_type_info={
        "description": "New test data type for API demonstration.",
        "version": "2.0",
    }
)
print(f"Data Type Info set: {data_type.get_info()}")

# Check if Data Type exists
data_type_exists = DataType.exists(data_type_name="Test Data Type")
print(f"Does Data Type exist? {data_type_exists}")

# Delete Data Type
data_type.delete()
print(f"Data Type deleted: {data_type}")

# Check if Data Type exists after deletion
data_type_exists_after_deletion = DataType.exists(data_type_name="Test Data Type")
print(f"Does Data Type exist after deletion? {data_type_exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing data types using the GEMINIbase API:

*   **Creating a data type:** The `DataType.create()` method is used to create a new data type with a name and additional information (description, version).
*   **Getting a data type:** The `DataType.get_by_id()` method retrieves a data type by its unique ID. The `DataType.get()` method retrieves a data type by its name.
*   **Getting all data types:** The `DataType.get_all()` method retrieves all data types in the database.
*   **Searching for data types:** The `DataType.search()` method finds data types based on specified criteria, such as the name.
*   **Updating a data type:** The `DataType.update()` method updates the attributes of an existing data type.
*   **Setting data type information:** The `DataType.set_info()` method updates the `data_type_info` field with new data.
*   **Checking for existence:** The `DataType.exists()` method verifies if a data type with the given name exists.
*   **Deleting a data type:** The `DataType.delete()` method removes the data type from the database.
