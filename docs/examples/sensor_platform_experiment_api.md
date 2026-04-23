# Sensor Platform Experiment API Example

This example demonstrates how to associate and unassociate experiments with sensor platforms using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_platform_experiment_api.py`.

## Code

```python
from gemini.api.sensor_platform import SensorPlatform

# Create a new Sensor Platform for Experiment A
new_sensor_platform = SensorPlatform.create(
    sensor_platform_name="Platform Test 1",
    sensor_platform_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Sensor Platform: {new_sensor_platform}")

# Get Associated Experiments
associated_experiments = new_sensor_platform.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the new sensor platform with Experiment B
new_sensor_platform.associate_experiment(experiment_name="Experiment B")
print(f"Associated Sensor Platform with Experiment B")

# Check if the new sensor platform is associated with Experiment B
is_associated = new_sensor_platform.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Sensor Platform associated with Experiment B? {is_associated}")

# Unassociate the new sensor platform from Experiment B
new_sensor_platform.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Sensor Platform from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_sensor_platform.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Sensor Platform still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between experiments and sensor platforms:

*   **Creating a sensor platform:** The `SensorPlatform.create()` method is used to create a new sensor platform with a name, additional information, and associated experiment.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the sensor platform.
*   **Associating with an experiment:** The `associate_experiment()` method associates the sensor platform with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the sensor platform is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the sensor platform and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the sensor platform is no longer associated with Experiment B.
