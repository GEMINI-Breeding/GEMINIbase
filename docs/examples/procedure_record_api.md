# Procedure Record API Example

This example demonstrates how to use the ProcedureRecord API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/procedure_record_api.py`.

## Code

```python
from gemini.api.procedure_record import ProcedureRecord
from datetime import datetime, timedelta
from random import randint

timestamp = datetime(1994, 10, 1, 12, 0, 0)  # Fixed timestamp for consistency
timestamp = timestamp + timedelta(hours=randint(0, 23), minutes=randint(0, 59))  # Randomize time within the day

# Create a new Procedure Record for Procedure A, with Experiment A, Site A1 and Season 1A
new_procedure_record = ProcedureRecord.create(
    timestamp=timestamp,
    collection_date=timestamp.date(),
    procedure_name="Procedure A",
    dataset_name="Procedure A Dataset",
    procedure_data={"key": "value"},
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A",
    record_info={"test": "test"},
    insert_on_create=True
)
print(f"Created Procedure Record: {new_procedure_record}")

# Get Procedure Record by ID
procedure_record_by_id = ProcedureRecord.get_by_id(new_procedure_record.id)
print(f"Procedure Record by ID: {procedure_record_by_id}")

# Get Procedure Record
procedure_record_by_name = ProcedureRecord.get(
    timestamp=new_procedure_record.timestamp,
    procedure_name="Procedure A",
    dataset_name="Procedure A Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Procedure Record by Name: {procedure_record_by_name}")

# Get all Procedure Records limit by 10
procedure_records = ProcedureRecord.get_all(limit=10)
print(f"Procedure Records (limit 10):")
for record in procedure_records:
    print(record)

# Search Procedure Records
searched_records = ProcedureRecord.search(
    experiment_name="Experiment A"
)
searched_records = list(searched_records)  # Convert to list to evaluate the generator
print(f"Found {len(searched_records)} records in Experiment A:")

# Update the newly created Procedure Record
updated_record = new_procedure_record.update(
    procedure_data={"key": "new_value"},
    record_info={"test": "test_updated"}
)
print(f"Updated Procedure Record: {updated_record}")

# Set Procedure Record Info
updated_record.set_info(
    record_info={"test": "test_set_info"}
)
print(f"Procedure Record Info set: {updated_record.get_info()}")

# Check if Procedure Record exists
exists = ProcedureRecord.exists(
    timestamp=new_procedure_record.timestamp,
    procedure_name="Procedure A",
    dataset_name="Procedure A Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Does Procedure Record exist? {exists}")

# Delete Procedure Record
is_deleted = updated_record.delete()
print(f"Procedure Record deleted: {is_deleted}")

# Check if Procedure Record exists after deletion
exists = ProcedureRecord.exists(
    timestamp=new_procedure_record.timestamp,
    procedure_name="Procedure A",
    dataset_name="Procedure A Dataset",
    experiment_name="Experiment A",
    site_name="Site A1",
    season_name="Season 1A"
)
print(f"Does Procedure Record exist after deletion? {exists}")
```

## Explanation

This example demonstrates the basic operations for managing procedure records using the GEMINIbase API:

*   **Creating a procedure record:** The `ProcedureRecord.create()` method is used to create a new procedure record with a timestamp, collection date, associated procedure, dataset, additional data, and associated experiment, site, and season.
*   **Getting a procedure record:** The `ProcedureRecord.get_by_id()` method retrieves a procedure record by its unique ID. The `ProcedureRecord.get()` method retrieves a procedure record by its timestamp, procedure name, dataset name, and associated experiment, site, and season.
*   **Getting all procedure records:** The `ProcedureRecord.get_all()` method retrieves all procedure records, with an optional limit.
*   **Searching for procedure records:** The `ProcedureRecord.search()` method finds procedure records based on specified criteria, such as the experiment name.
*   **Updating a procedure record:** The `ProcedureRecord.update()` method updates the attributes of an existing procedure record.
*   **Setting procedure record information:** The `ProcedureRecord.set_info()` method updates the `record_info` field with new data.
*   **Checking for existence:** The `ProcedureRecord.exists()` method verifies if a procedure record with the given attributes exists.
*   **Deleting a procedure record:** The `ProcedureRecord.delete()` method removes the procedure record from the database.
