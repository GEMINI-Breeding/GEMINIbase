# Sensor API Example

This example demonstrates how to use the Sensor API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_api.py`.

## Code

```python
from gemini.api.sensor import Sensor
from gemini.api.sensor import GEMINISensorType, GEMINIDataType, GEMINIDataFormat

# Create a new Sensor for Experiment A
new_sensor = Sensor.create(
    sensor_name="Sensor A",
    sensor_type=GEMINISensorType.Calibration,
    sensor_data_format=GEMINIDataFormat.CSV,
    sensor_data_type=GEMINIDataType.Text,
    sensor_info={"test": "test"},
    experiment_name="Experiment A",
    sensor_platform_name="Platform A"
)
print(f"Created New Sensor: {new_sensor}")

# Get Sensor by ID
sensor_by_id = Sensor.get_by_id(new_sensor.id)
print(f"Got Sensor by ID: {sensor_by_id}")

# Get Sensor by Name
sensor_by_name = Sensor.get(sensor_name="Sensor A")
print(f"Got Sensor by Name: {sensor_by_name}")

# Get all Sensors
all_sensors = Sensor.get_all()
for sensor in all_sensors:
    print(f"Sensor: {sensor}")

# Search for Sensors by Name
search_results = Sensor.search(sensor_name="Sensor A")
for result in search_results:
    print(f"Search Result: {result}")

# Update Sensor
sensor_by_name.update(
    sensor_data_format=GEMINIDataFormat.JSON,
    sensor_info={"updated": "info"}
)
print(f"Updated Sensor: {sensor_by_name}")

# Refresh Sensor
sensor_by_name.refresh()
print(f"Refreshed Sensor: {sensor_by_name}")

# Set Sensor Info
sensor_by_name.set_info(
    sensor_info={"new": "info"}
)
print(f"Set Sensor Info: {sensor_by_name.get_info()}")

# Check if Sensor Exists
exists = Sensor.exists(sensor_name="Sensor A")
print(f"Does Sensor Exist? {exists}")

# Delete Sensor
is_deleted = sensor_by_name.delete()
print(f"Deleted Sensor: {is_deleted}")

# Check if Sensor Exists after Deletion
exists_after_deletion = Sensor.exists(sensor_name="Sensor A")
print(f"Does Sensor Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing sensors using the GEMINIbase API:

*   **Creating a sensor:** The `Sensor.create()` method is used to create a new sensor with a name, type, data format, data type, additional information, and associated experiment and sensor platform.
*   **Getting a sensor:** The `Sensor.get_by_id()` method retrieves a sensor by its unique ID. The `Sensor.get()` method retrieves a sensor by its name.
*   **Getting all sensors:** The `Sensor.get_all()` method retrieves all sensors in the database.
*   **Searching for sensors:** The `Sensor.search()` method finds sensors based on specified criteria, such as the name.
*   **Updating a sensor:** The `Sensor.update()` method updates the attributes of an existing sensor.
*   **Refreshing a sensor:** The `Sensor.refresh()` method updates the sensor object with the latest data from the database.
*   **Setting sensor information:** The `Sensor.set_info()` method updates the `sensor_info` field with new data.
*   **Checking for existence:** The `Sensor.exists()` method verifies if a sensor with the given name exists.
*   **Deleting a sensor:** The `Sensor.delete()` method removes the sensor from the database.
