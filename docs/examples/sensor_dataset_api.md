# Sensor Dataset API Example

This example demonstrates how to use the Sensor and Dataset APIs to associate datasets with sensors in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_dataset_api.py`.

## Code

```python
from gemini.api.sensor import Sensor
from gemini.api.dataset import Dataset, GEMINIDatasetType

# Create a new Sensor for Experiment A
new_sensor = Sensor.create(
    sensor_name="Sensor Test 1",
    sensor_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Sensor: {new_sensor}")

# Create a new Dataset for Experiment A
new_dataset = Dataset.create(
    dataset_name="Dataset Test 1",
    dataset_type=GEMINIDatasetType.Sensor,
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset: {new_dataset}")

# Create a new Dataset for New Sensor directly
new_sensor_dataset = new_sensor.create_new_dataset(
    dataset_name="Sensor Test 1 Dataset",
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset for New Sensor: {new_sensor_dataset}")

# Associate the new dataset with the new sensor
new_sensor.associate_dataset(dataset_name=new_dataset.dataset_name)
print(f"Associated New Dataset with New Sensor: {new_sensor}")

# Print the associated datasets
associated_datasets = new_sensor.get_associated_datasets()
for dataset in associated_datasets:
    print(f"Associated Dataset: {dataset}")
```

## Explanation

This example demonstrates how to manage the association between datasets and sensors:

*   **Creating a sensor:** The `Sensor.create()` method is used to create a new sensor with a name and additional information.
*   **Creating a dataset:** The `Dataset.create()` method is used to create a new dataset with a name, type, additional information, collection date, and associated experiment.
*   **Creating a dataset for a sensor:** The `Sensor.create_new_dataset()` method is used to create a new dataset and automatically associate it with the sensor.
*   **Associating with a dataset:** The `associate_dataset()` method associates the sensor with the created dataset.
*   **Getting associated datasets:** The `get_associated_datasets()` method retrieves a list of datasets associated with the sensor.
