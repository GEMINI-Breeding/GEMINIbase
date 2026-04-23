# Trait Record API Example

This example demonstrates how to use the TraitRecord API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/trait_record_api.py`.

## Code

```python
from gemini.api.trait_record import TraitRecord
from datetime import datetime, timedelta
from random import randint

timestamp = datetime(1994, 10, 1, 12, 0, 0)  # Fixed timestamp for consistency
timestamp = timestamp + timedelta(hours=randint(0, 23), minutes=randint(0, 59))  # Randomize time within the day

new_trait_record = TraitRecord.create(
    timestamp=timestamp,
    collection_date=timestamp.date(),
    trait_name="Trait A1",
    dataset_name="Trait A1 Dataset",
    trait_value=42.0,
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    record_info={"test": "test"},
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1,
    insert_on_create=True
)
print(f"Created Trait Record: {new_trait_record}")

# Get Trait Record by ID
trait_record_by_id = TraitRecord.get_by_id(new_trait_record.id)
print(f"Trait Record by ID: {trait_record_by_id}")

# Get Trait Record
trait_record_by_name = TraitRecord.get(
    timestamp=new_trait_record.timestamp,
    trait_name="Trait A1",
    dataset_name="Trait A1 Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1
)
print(f"Trait Record by Name: {trait_record_by_name}")

# Get all Trait Records limit by 10
trait_records = TraitRecord.get_all(limit=10)
print(f"Trait Records (limit 10):")
for record in trait_records:
    print(record)

# Search Trait Records
searched_records = TraitRecord.search(
    experiment_name="Experiment A"
)
searched_records = list(searched_records)  # Convert to list to evaluate the generator
print(f"Found {len(searched_records)} records in Experiment A:")

# Update the newly created Trait Record
updated_record = new_trait_record.update(
    trait_value=43.0,
    record_info={"test": "test_updated"}
)
print(f"Updated Trait Record: {updated_record}")

# Set Trait Record Info
updated_record.set_info(
    record_info={"test": "test_set_info"}
)
print(f"Set Trait Record Info: {updated_record.get_info()}")

# Check if Trait Record exists
exists = TraitRecord.exists(
    timestamp=new_trait_record.timestamp,
    trait_name="Trait A1",
    dataset_name="Trait A1 Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1
)
print(f"Does Trait Record Exist? {exists}")

# Delete Trait Record
deleted_record = new_trait_record.delete()
print(f"Trait Record deleted: {deleted_record}")

# Check if Trait Record exists after deletion
exists_after_deletion = TraitRecord.exists(
    timestamp=new_trait_record.timestamp,
    trait_name="Trait A1",
    dataset_name="Trait A1 Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    plot_number=1,
    plot_row_number=1,
    plot_column_number=1
)
print(f"Does Trait Record Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing trait records using the GEMINIbase API:

*   **Creating a trait record:** The `TraitRecord.create()` method is used to create a new trait record with a timestamp, collection date, associated trait, dataset, trait value, and associated experiment, site, season, and plot.
*   **Getting a trait record:** The `TraitRecord.get_by_id()` method retrieves a trait record by its unique ID. The `TraitRecord.get()` method retrieves a trait record by its timestamp, trait name, dataset name, and associated experiment, site, season, and plot.
*   **Getting all trait records:** The `TraitRecord.get_all()` method retrieves all trait records, with an optional limit.
*   **Searching for trait records:** The `TraitRecord.search()` method finds trait records based on specified criteria, such as the experiment name.
*   **Updating a trait record:** The `TraitRecord.update()` method updates the attributes of an existing trait record.
*   **Setting trait record information:** The `TraitRecord.set_info()` method updates the `record_info` field with new data.
*   **Checking for existence:** The `TraitRecord.exists()` method verifies if a trait record with the given attributes exists.
*   **Deleting a trait record:** The `TraitRecord.delete()` method removes the trait record from the database.
