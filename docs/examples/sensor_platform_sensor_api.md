# Sensor Platform Sensor API Example

This example demonstrates how to associate and unassociate sensors with sensor platforms using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_platform_sensor_api.py`.

## Code

```python
from gemini.api.sensor_platform import SensorPlatform
from gemini.api.sensor import Sensor

# Create a new Sensor Platform for Experiment A
new_sensor_platform = SensorPlatform.create(
    sensor_platform_name="Platform Test 1",
    sensor_platform_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Sensor Platform: {new_sensor_platform}")

# Create a new Sensor for Experiment A and Platform Test 1
new_sensor = Sensor.create(
    sensor_name="Sensor Test 1",
    sensor_info={"test": "test"},
    experiment_name="Experiment A",
    sensor_platform_name="Platform Test 1"
)
print(f"Created New Sensor: {new_sensor}")

# Create a new sensor directly
new_sensor_direct = Sensor.create(
    sensor_name="Sensor Test 2",
    sensor_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Sensor Directly: {new_sensor_direct}")

# List Associated Sensor Platforms
associated_sensors = new_sensor_platform.get_associated_sensors()
for sensor in associated_sensors:
    print(f"Associated Sensor: {sensor}")

# Check if the new sensor is associated with Platform Test 1
is_associated = new_sensor_platform.belongs_to_sensor(sensor_name="Sensor Test 1")
print(f"Is Sensor Test 1 associated with Platform Test 1? {is_associated}")

# Unassociate the new sensor from Platform Test 1
new_sensor_platform.unassociate_sensor(sensor_name="Sensor Test 1")
print(f"Unassociated Sensor Test 1 from Platform Test 1")

# Verify the unassociation
is_associated_after_unassociation = new_sensor_platform.belongs_to_sensor(sensor_name="Sensor Test 1")
print(f"Is Sensor Test 1 still associated with Platform Test 1? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between sensors and sensor platforms:

*   **Creating a sensor platform:** The `SensorPlatform.create()` method is used to create a new sensor platform with a name and additional information.
*   **Creating a sensor:** The `Sensor.create()` method is used to create a new sensor with a name and additional information, and associated experiment and sensor platform.
*   **Creating a sensor directly:** The `Sensor.create()` method is used to create a new sensor without associating it with a sensor platform.
*   **Getting associated sensors:** The `get_associated_sensors()` method retrieves a list of sensors associated with the sensor platform.
*   **Checking association:** The `belongs_to_sensor()` method verifies if the sensor platform is associated with a specific sensor.
*   **Unassociating from a sensor:** The `unassociate_sensor()` method removes the association between the sensor platform and the sensor.
*   **Verifying unassociation:** The `belongs_to_sensor()` method is used again to confirm that the sensor platform is no longer associated with the sensor.
