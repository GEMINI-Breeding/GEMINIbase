# Sensor Experiment API Example

This example demonstrates how to associate and unassociate experiments with sensors using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_experiment_api.py`.

## Code

```python
from gemini.api.sensor import Sensor

# Create a new Sensor for Experiment A
new_sensor = Sensor.create(
    sensor_name="Sensor X",
    sensor_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Sensor: {new_sensor}")

# Get Associated Experiments
associated_experiments = new_sensor.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the new sensor with Experiment B
new_sensor.associate_experiment(experiment_name="Experiment B")
print(f"Associated Sensor with Experiment B")

# Check if the new sensor is associated with Experiment B
is_associated = new_sensor.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Sensor associated with Experiment B? {is_associated}")

# Unassociate the new sensor from Experiment B
new_sensor.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Sensor from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_sensor.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Sensor still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between experiments and sensors:

*   **Creating a sensor:** The `Sensor.create()` method is used to create a new sensor with a name and additional information.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the sensor.
*   **Associating with an experiment:** The `associate_experiment()` method associates the sensor with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the sensor is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the sensor and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the sensor is no longer associated with Experiment B.
