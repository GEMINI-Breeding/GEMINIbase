# Dataset Record API Example

This example demonstrates how to use the DatasetRecord API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/dataset_record_api.py`.

## Code

```python
from gemini.api.dataset_record import DatasetRecord
from datetime import datetime, timedelta
from random import randint

timestamp = datetime(1994, 10, 1, 12, 0, 0)  # Fixed timestamp for consistency
timestamp = timestamp + timedelta(hours=randint(0, 23), minutes=randint(0, 59))  # Randomize time within the day

# Create a new Dataset Record for Dataset A, with Experiment A, Site A1 and Season 1A
new_dataset_record = DatasetRecord.create(
    timestamp=timestamp,
    collection_date=timestamp.date(),
    dataset_name="Dataset A",
    dataset_data={"key": "value"},
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    record_info={"test": "test"},
    insert_on_create=True
)
print(f"Created Dataset Record: {new_dataset_record}")

# Get Dataset Record by ID
dataset_record_by_id = DatasetRecord.get_by_id(new_dataset_record.id)
print(f"Dataset Record by ID: {dataset_record_by_id}")

# Get Dataset Record
dataset_record_by_name = DatasetRecord.get(
    timestamp=new_dataset_record.timestamp,
    dataset_name="Dataset A",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Dataset Record by Name: {dataset_record_by_name}")

# Get all Dataset Records limit by 10
dataset_records = DatasetRecord.get_all(limit=10)
print(f"Dataset Records (limit 10):")
for record in dataset_records:
    print(record)

# Search Dataset Records
searched_records = DatasetRecord.search(
    experiment_name="Experiment A"
)
searched_records = list(searched_records)  # Convert to list to evaluate the generator
print(f"Found {len(searched_records)} records in Experiment A:")

# Update the newly created Dataset Record
updated_record = new_dataset_record.update(
    dataset_data={"key": "new_value"},
    record_info={"test": "test_updated"}
)
print(f"Updated Dataset Record: {updated_record}")

# Set Dataset Record Info
updated_record.set_info(
    record_info={"test": "test_set_info"}
)
print(f"Dataset Record Info set: {updated_record.get_info()}")

# Check if Dataset Record exists
exists = DatasetRecord.exists(
    timestamp=new_dataset_record.timestamp,
    dataset_name="Dataset A",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Does Dataset Record exist? {exists}")

# Delete Dataset Record
is_deleted = new_dataset_record.delete()
print(f"Dataset Record deleted: {is_deleted}")

# Check if Dataset Record exists after deletion
exists_after_deletion = DatasetRecord.exists(
    timestamp=new_dataset_record.timestamp,
    dataset_name="Dataset A",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Does Dataset Record exist after deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing dataset records using the GEMINIbase API:

*   **Creating a dataset record:** The `DatasetRecord.create()` method is used to create a new dataset record with a timestamp, collection date, associated dataset, experiment, site, and season.
*   **Getting a dataset record:** The `DatasetRecord.get_by_id()` method retrieves a dataset record by its unique ID. The `DatasetRecord.get()` method retrieves a dataset record by its timestamp, dataset name, experiment name, site name, and season name.
*   **Getting all dataset records:** The `DatasetRecord.get_all()` method retrieves all dataset records, with an optional limit.
*   **Searching for dataset records:** The `DatasetRecord.search()` method finds dataset records based on specified criteria, such as the experiment name.
*   **Updating a dataset record:** The `DatasetRecord.update()` method updates the attributes of an existing dataset record.
*   **Setting dataset record information:** The `DatasetRecord.set_info()` method updates the `record_info` field with new data.
*   **Checking for existence:** The `DatasetRecord.exists()` method verifies if a dataset record with the given attributes exists.
*   **Deleting a dataset record:** The `DatasetRecord.delete()` method removes the dataset record from the database.
