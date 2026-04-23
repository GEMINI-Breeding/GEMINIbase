# Sensor Type API Example

This example demonstrates how to use the SensorType API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_type_api.py`.

## Code

```python
from gemini.api.sensor_type import SensorType

# Create a new Sensor Type
new_sensor_type = SensorType.create(
    name="Temperature",
    description="Measures temperature",
    info={"units": "Celsius"}
)
print(f"Created New Sensor Type: {new_sensor_type}")

# Get Sensor Type by ID
sensor_type_by_id = SensorType.get_by_id(new_sensor_type.id)
print(f"Got Sensor Type by ID: {sensor_type_by_id}")

# Get Sensor Type by Name
sensor_type_by_name = SensorType.get(name="Temperature")
print(f"Got Sensor Type by Name: {sensor_type_by_name}")

# Get all Sensor Types
all_sensor_types = SensorType.get_all()
for sensor_type in all_sensor_types:
    print(f"Sensor Type: {sensor_type}")

# Search for Sensor Types by Name
search_results = SensorType.search(name="Temperature")
for result in search_results:
    print(f"Search Result: {result}")

# Update Sensor Type
sensor_type_by_name.update(
    description="Measures temperature in Celsius"
)
print(f"Updated Sensor Type: {sensor_type_by_name}")

# Refresh Sensor Type
sensor_type_by_name.refresh()
print(f"Refreshed Sensor Type: {sensor_type_by_name}")

# Set Sensor Type Info
sensor_type_by_name.set_info(
    info={"units": "Fahrenheit"}
)
print(f"Set Sensor Type Info: {sensor_type_by_name.get_info()}")

# Check if Sensor Type Exists
exists = SensorType.exists(name="Temperature")
print(f"Does Sensor Type Exist? {exists}")

# Delete Sensor Type
is_deleted = sensor_type_by_name.delete()
print(f"Deleted Sensor Type: {is_deleted}")

# Check if Sensor Type Exists after Deletion
exists_after_deletion = SensorType.exists(name="Temperature")
print(f"Does Sensor Type Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing sensor types using the GEMINIbase API:

*   **Creating a sensor type:** The `SensorType.create()` method is used to create a new sensor type with a name, description, and additional information.
*   **Getting a sensor type:** The `SensorType.get_by_id()` method retrieves a sensor type by its unique ID. The `SensorType.get()` method retrieves a sensor type by its name.
*   **Getting all sensor types:** The `SensorType.get_all()` method retrieves all sensor types in the database.
*   **Searching for sensor types:** The `SensorType.search()` method finds sensor types based on specified criteria, such as the name.
*   **Updating a sensor type:** The `SensorType.update()` method updates the attributes of an existing sensor type.
*   **Refreshing a sensor type:** The `SensorType.refresh()` method updates the sensor type object with the latest data from the database.
*   **Setting sensor type information:** The `SensorType.set_info()` method updates the `info` field with new data.
*   **Checking for existence:** The `SensorType.exists()` method verifies if a sensor type with the given name exists.
*   **Deleting a sensor type:** The `SensorType.delete()` method removes the sensor type from the database.
