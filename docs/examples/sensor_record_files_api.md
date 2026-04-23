# Sensor Record Files API Example

This example demonstrates how to use the SensorRecord API to associate files with sensor records in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/sensor_record_files_api.py`.

## Code

```python
from gemini.api.sensor_record import SensorRecord
from datetime import datetime, timedelta
from random import randint, uniform
import os

# Create Timestamp
timestamp = datetime(1994, 10, 1, 12, 0, 0)  # Fixed timestamp for consistency
timestamp = timestamp + timedelta(hours=randint(0, 23), minutes=randint(0, 59))  # Randomize time within the day

# Get Sample Image Folder
script_folder = os.path.dirname(os.path.abspath(__file__))
sample_image_folder = os.path.join(script_folder, "sample_images")
sample_image_files = [
    os.path.join(sample_image_folder, f) for f in os.listdir(sample_image_folder)
    if os.path.isfile(os.path.join(sample_image_folder, f))
]
print(f"Sample Image Files: {sample_image_files}")

# Creating Records to add to SensorRecord
records_to_add = []
for image_file in sample_image_files:
    timestamp = timestamp + timedelta(minutes=randint(1, 60))  # Increment timestamp for each file
    collection_date = timestamp.date()  # Use the date part of the timestamp
    record = SensorRecord.create(
        timestamp=timestamp,
        collection_date=collection_date,
        sensor_name="Sensor A",
        dataset_name="Sensor A Images Dataset",
        sensor_data={"value": uniform(0, 100)},
        experiment_name="Experiment A",
        site_name="Site A1",
        season_name="Season 1A",
        record_file=image_file,
        record_info={"test": "test"},
        insert_on_create=False
    )
    records_to_add.append(record)

SensorRecord.insert(records_to_add)

# Search the Sensor Records
searched_records = SensorRecord.search(
    collection_date=timestamp.date(),
    sensor_name="Sensor A",
    dataset_name="Sensor A Images Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
searched_records = list(searched_records)  # Convert to list to evaluate the generator

# Print the searched records
print(f"Found {len(searched_records)} records in Sensor A, Experiment A, Site A1, Season 1A:")
for record in searched_records:
    print(record)
```

## Explanation

This example demonstrates how to associate files with sensor records using the GEMINIbase API:

*   **Creating sensor records with files:** The `SensorRecord.create()` method is used to create new sensor records, each associated with a file from the `sample_images` directory. The `insert_on_create` parameter is set to `False` to allow batch insertion.
*   **Inserting sensor records:** The `SensorRecord.insert()` method is used to efficiently insert multiple sensor records into the database.
*   **Searching for sensor records:** The `SensorRecord.search()` method is used to find sensor records based on specified criteria.
