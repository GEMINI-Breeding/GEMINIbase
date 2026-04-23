# Script Record Files API Example

This example demonstrates how to use the ScriptRecord API to associate files with script records in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/script_record_files_api.py`.

## Code

```python
from gemini.api.script_record import ScriptRecord
from datetime import datetime, timedelta
from random import randint
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

# Creating Records to add to ScriptRecord
records_to_add = []
for image_file in sample_image_files:
    timestamp = timestamp + timedelta(minutes=randint(1, 60))  # Increment timestamp for each file
    collection_date = timestamp.date()  # Use the date part of the timestamp
    record = ScriptRecord.create(
        timestamp=timestamp,
        collection_date=collection_date,
        script_name="Script A",
        dataset_name="Script A Images Dataset",
        script_data={"key": "value"},
        experiment_name="Experiment A",
        site_name="Site A1",
        season_name="Season 1A",
        record_file=image_file,
        record_info={"test": "test"},
        insert_on_create=False
    )
    records_to_add.append(record)

ScriptRecord.insert(records_to_add)

# Search the Script Records
searched_records = ScriptRecord.search(
    collection_date=timestamp.date(),
    script_name="Script A",
    dataset_name="Script A Images Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
searched_records = list(searched_records)  # Convert to list to evaluate the generator

# Print the searched records
print(f"Found {len(searched_records)} records in Script A, Experiment A, Site A1, Season 1A:")
for record in searched_records:
    print(record)
```

## Explanation

This example demonstrates how to associate files with script records using the GEMINIbase API:

*   **Creating script records with files:** The `ScriptRecord.create()` method is used to create new script records, each associated with a file from the `sample_images` directory. The `insert_on_create` parameter is set to `False` to allow batch insertion.
*   **Inserting script records:** The `ScriptRecord.insert()` method is used to efficiently insert multiple script records into the database.
*   **Searching for script records:** The `ScriptRecord.search()` method is used to find script records based on specified criteria.
