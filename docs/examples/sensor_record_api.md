# Sensor Record API Example

This example demonstrates how to use the SensorRecord API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_record_api.py`.

## Code

```python
from gemini.api.sensor_record import SensorRecord
from datetime import datetime, timedelta
from random import randint

timestamp = datetime(1994, 10, 1, 12, 0, 0)  # Fixed timestamp for consistency
timestamp = timestamp + timedelta(hours=randint(0, 23), minutes=randint(0, 59))  # Randomize time within the day

# Create a new Sensor Record for Sensor A, with Experiment A, Site A1 and Season 1A
new_sensor_record = SensorRecord.create(
    timestamp=timestamp,
    collection_date=timestamp.date(),
    sensor_name="Sensor A1",
    dataset_name="Sensor A1 Dataset",
    sensor_data={"key": "value"},
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    record_info={"test": "test"},
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1,
    insert_on_create=True
)
print(f"Created Sensor Record: {new_sensor_record}")

# Get Sensor Record by ID
sensor_record_by_id = SensorRecord.get_by_id(new_sensor_record.id)
print(f"Sensor Record by ID: {sensor_record_by_id}")

# Get Sensor Record
sensor_record_by_name = SensorRecord.get(
    timestamp=new_sensor_record.timestamp,
    sensor_name="Sensor A1",
    dataset_name="Sensor A1 Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1
)
print(f"Sensor Record by Name: {sensor_record_by_name}")

# Get all Sensor Records limit by 10
sensor_records = SensorRecord.get_all(limit=10)
print(f"Sensor Records (limit 10):")
for record in sensor_records:
    print(record)

# Search Sensor Records
searched_records = SensorRecord.search(
    experiment_name="Experiment A"
)
searched_records = list(searched_records)  # Convert to list to evaluate the generator
print(f"Found {len(searched_records)} records in Experiment A:")

# Update the newly created Sensor Record
updated_record = new_sensor_record.update(
    sensor_data={"key": "new_value"},
    record_info={"test": "test_updated"}
)
print(f"Updated Sensor Record: {updated_record}")

# Set Sensor Record Info
updated_record.set_info(
    record_info={"test": "test_set_info"}
)
print(f"Set Sensor Record Info: {updated_record.get_info()}")

# Check if Sensor Record Exists
exists = SensorRecord.exists(
    timestamp=new_sensor_record.timestamp,
    sensor_name="Sensor A1",
    dataset_name="Sensor A1 Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1
)
print(f"Does Sensor Record Exist? {exists}")

# Delete Sensor Record
is_deleted = new_sensor_record.delete()
print(f"Deleted Sensor Record: {is_deleted}")

# Check if Sensor Record Exists after Deletion
exists_after_deletion = SensorRecord.exists(
    timestamp=new_sensor_record.timestamp,
    sensor_name="Sensor A1",
    dataset_name="Sensor A1 Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1
)
print(f"Does Sensor Record Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing sensor records using the GEMINIbase API:

*   **Creating a sensor record:** The `SensorRecord.create()` method is used to create a new sensor record with a timestamp, collection date, associated sensor, dataset, additional data, and associated experiment, site, season, and plot.
*   **Getting a sensor record:** The `SensorRecord.get_by_id()` method retrieves a sensor record by its unique ID. The `SensorRecord.get()` method retrieves a sensor record by its timestamp, sensor name, dataset name, and associated experiment, site, season, and plot.
*   **Getting all sensor records:** The `SensorRecord.get_all()` method retrieves all sensor records, with an optional limit.
*   **Searching for sensor records:** The `SensorRecord.search()` method finds sensor records based on specified criteria, such as the experiment name.
*   **Updating a sensor record:** The `SensorRecord.update()` method updates the attributes of an existing sensor record.
*   **Setting sensor record information:** The `SensorRecord.set_info()` method updates the `record_info` field with new data.
*   **Checking for existence:** The `SensorRecord.exists()` method verifies if a sensor record with the given attributes exists.
*   **Deleting a sensor record:** The `SensorRecord.delete()` method removes the sensor record from the database.
