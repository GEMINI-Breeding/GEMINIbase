# Script Record API Example

This example demonstrates how to use the ScriptRecord API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/script_record_api.py`.

## Code

```python
from gemini.api.script import ScriptRecord
from datetime import datetime, timedelta
from random import randint

timestamp = datetime(1994, 10, 1, 12, 0, 0)  # Fixed timestamp for consistency
timestamp = timestamp + timedelta(hours=randint(0, 23), minutes=randint(0, 59))  # Randomize time within the day

# Create a new Script Record for Script A, with Experiment A, Site A1 and Season 1A
new_script_record = ScriptRecord.create(
    timestamp=timestamp,
    collection_date=timestamp.date(),
    script_name="Script A",
    dataset_name="Script A Dataset",
    script_data={"key": "value"},
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    record_info={"test": "test"},
    insert_on_create=True
)
print(f"Created Script Record: {new_script_record}")

# Get Script Record by ID
script_record_by_id = ScriptRecord.get_by_id(new_script_record.id)
print(f"Script Record by ID: {script_record_by_id}")

# Get Script Record
script_record_by_name = ScriptRecord.get(
    timestamp=new_script_record.timestamp,
    script_name="Script A",
    dataset_name="Script A Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Script Record by Name: {script_record_by_name}")

# Get all Script Records limit by 10
script_records = ScriptRecord.get_all(limit=10)
print(f"Script Records (limit 10):")
for record in script_records:
    print(record)

# Search Script Records
searched_records = ScriptRecord.search(
    experiment_name="Experiment A"
)
searched_records = list(searched_records)  # Convert to list to evaluate the generator
print(f"Found {len(searched_records)} records in Experiment A:")

# Update the newly created Script Record
updated_record = new_script_record.update(
    script_data={"key": "new_value"},
    record_info={"test": "test_updated"}
)
print(f"Updated Script Record: {updated_record}")

# Set Script Record Info
updated_record.set_info(
    record_info={"test": "test_set_info"}
)
print(f"Script Record Info set: {updated_record.get_info()}")

# Check if Script Record exists
exists = ScriptRecord.exists(
    timestamp=new_script_record.timestamp,
    script_name="Script A",
    dataset_name="Script A Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Does Script Record Exist? {exists}")

# Delete Script Record
is_deleted = updated_record.delete()
print(f"Deleted Script Record: {is_deleted}")

# Check if Script Record exists after deletion
exists_after_deletion = ScriptRecord.exists(
    timestamp=new_script_record.timestamp,
    script_name="Script A",
    dataset_name="Script A Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Does Script Record Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing script records using the GEMINIbase API:

*   **Creating a script record:** The `ScriptRecord.create()` method is used to create a new script record with a timestamp, collection date, associated script, dataset, additional data, and associated experiment, site, and season.
*   **Getting a script record:** The `ScriptRecord.get_by_id()` method retrieves a script record by its unique ID. The `ScriptRecord.get()` method retrieves a script record by its timestamp, script name, dataset name, and associated experiment, site, and season.
*   **Getting all script records:** The `ScriptRecord.get_all()` method retrieves all script records, with an optional limit.
*   **Searching for script records:** The `ScriptRecord.search()` method finds script records based on specified criteria, such as the experiment name.
*   **Updating a script record:** The `ScriptRecord.update()` method updates the attributes of an existing script record.
*   **Setting script record information:** The `ScriptRecord.set_info()` method updates the `record_info` field with new data.
*   **Checking for existence:** The `ScriptRecord.exists()` method verifies if a script record with the given attributes exists.
*   **Deleting a script record:** The `ScriptRecord.delete()` method removes the script record from the database.
