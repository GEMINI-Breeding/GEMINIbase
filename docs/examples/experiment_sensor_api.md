# Experiment Sensor API Example

This example demonstrates how to associate and unassociate sensors with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_sensor_api.py`.

## Code

```python
from gemini.api.experiment import Experiment
from gemini.api.sensor import Sensor

# Create a new sensor for Experiment A
new_sensor = Sensor.create(
    sensor_name="New Sensor",
    sensor_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Sensor: {new_sensor}")

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new sensor
experiment_b.associate_sensor(sensor_name=new_sensor.sensor_name)
print(f"Associated New Sensor with Experiment B: {experiment_b}")

# Get Associated Sensors
associated_sensors = experiment_b.get_associated_sensors()
for sensor in associated_sensors:
    print(f"Associated Sensor: {sensor}")

# Check if the new sensor is associated with Experiment B
is_associated = experiment_b.belongs_to_sensor(sensor_name=new_sensor.sensor_name)
print(f"Is New Sensor associated with Experiment B? {is_associated}")

# Unassociate the new sensor from Experiment B
experiment_b.unassociate_sensor(sensor_name=new_sensor.sensor_name)
print(f"Unassociated New Sensor from Experiment B: {experiment_b}")

# Check if the new sensor is still associated with Experiment B
is_associated = experiment_b.belongs_to_sensor(sensor_name=new_sensor.sensor_name)
print(f"Is New Sensor still associated with Experiment B? {is_associated}")

# Create a new sensor for Experiment B
experiment_sensor = experiment_b.create_new_sensor(
    sensor_name="Experiment B Sensor",
    sensor_info={"test": "test"}
)
print(f"Created New Sensor: {experiment_sensor}")
```

## Explanation

This example demonstrates how to manage the association between sensors and experiments:

*   **Creating a sensor:** A new sensor is created and associated with Experiment A.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment B in this case).
*   **Associating with a sensor:** The `associate_sensor()` method associates the experiment with the created sensor.
*   **Getting associated sensors:** The `get_associated_sensors()` method retrieves a list of sensors associated with the experiment.
*   **Checking association:** The `belongs_to_sensor()` method verifies if the experiment is associated with a specific sensor.
*   **Unassociating from a sensor:** The `unassociate_sensor()` method removes the association between the experiment and the sensor.
*   **Verifying unassociation:** The `belongs_to_sensor()` method is used again to confirm that the experiment is no longer associated with the sensor.
*   **Creating a new sensor for an experiment:** The `create_new_sensor()` method creates a new sensor and automatically associates it with the experiment.
