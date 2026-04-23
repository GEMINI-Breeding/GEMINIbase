# Data Format Types API Example

This example demonstrates how to associate and unassociate data formats with data types using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/data_format_types_api.py`.

## Code

```python
from gemini.api.data_format import DataFormat
from gemini.api.data_type import DataType 

# Get the PNG data format
png_format = DataFormat.get("PNG")
print(f"PNG Data Format: {png_format}")

# Get associated data types
associated_data_types = png_format.get_associated_data_types()
for data_type in associated_data_types:
    print(f"Associated Data Type: {data_type}")

# Create a new data type
new_data_type = DataType.create(
    data_type_name="Test Data Type",
    data_type_info={
        "description": "This is a test data type for API demonstration.",
        "version": "1.0",
    }
)
print(f"Created new data type: {new_data_type}")

# Associate the new data type with the PNG data format
png_format.associate_data_type(data_type_name=new_data_type.data_type_name)
print(f"Associated data format {png_format.data_format_name} with data type {new_data_type.data_type_name}")

# Check if Belongs to Data Type
is_associated = png_format.belongs_to_data_type(data_type_name=new_data_type.data_type_name)
print(f"Is data format {png_format.data_format_name} associated with data type {new_data_type.data_type_name}? {is_associated}")

# Unassociate the data format from the data type
png_format.unassociate_data_type(data_type_name=new_data_type.data_type_name)
print(f"Unassociated data format {png_format.data_format_name} from data type {new_data_type.data_type_name}")

# Verify the unassociation
is_associated_after_unassociation = png_format.belongs_to_data_type(data_type_name=new_data_type.data_type_name)
print(f"Is data format {png_format.data_format_name} still associated with data type {new_data_type.data_type_name}? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between data formats and data types:

*   **Getting a data format:** The `DataFormat.get()` method retrieves a data format by its name (in this case, "PNG").
*   **Getting associated data types:** The `get_associated_data_types()` method retrieves a list of data types associated with the data format.
*   **Creating a data type:** A new data type is created with a name and additional information.
*   **Associating with a data type:** The `associate_data_type()` method associates the data format with the created data type.
*   **Checking association:** The `belongs_to_data_type()` method verifies if the data format is associated with a specific data type.
*   **Unassociating from a data type:** The `unassociate_data_type()` method removes the association between the data format and the data type.
*   **Verifying unassociation:** The `belongs_to_data_type()` method is used again to confirm that the data format is no longer associated with the data type.
