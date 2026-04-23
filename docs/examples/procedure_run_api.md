# Procedure Run API Example

This example demonstrates how to use the ProcedureRun API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/procedure_run_api.py`.

## Code

```python
from gemini.api.procedure_run import ProcedureRun

# Create a new procedure run
new_procedure_run = ProcedureRun.create(
    procedure_run_info={"test": "test"}
)
print(f"Created Procedure Run: {new_procedure_run}")

# Get ProcedureRun with procedure_run_info
procedure_run = ProcedureRun.get(
    procedure_run_info=new_procedure_run.procedure_run_info
)
print(f"Got Procedure Run: {procedure_run}")

# Get ProcedureRun by ID
procedure_run_by_id = ProcedureRun.get_by_id(new_procedure_run.id)
print(f"Got Procedure Run by ID: {procedure_run_by_id}")

# Get all procedure runs
all_procedure_runs = ProcedureRun.get_all()
print(f"All Procedure Runs:")
for proc_run in all_procedure_runs[:10]:
    print(proc_run)

# Search for procedure runs
searched_procedure_runs = ProcedureRun.search(
    procedure_run_info={"test": "test"}
)
length_searched_procedure_runs = len(searched_procedure_runs)
print(f"Found {length_searched_procedure_runs} procedure runs with procedure_run_info 'test': 'test'")

# Refresh the procedure run
procedure_run.refresh()
print(f"Refreshed Procedure Run: {procedure_run}")

# Update the procedure run
procedure_run.update(
    procedure_run_info={"test": "test_updated"}
)
print(f"Updated Procedure Run: {procedure_run}")

# Set Procedure Run Info
procedure_run.set_info(
    procedure_run_info={"test": "test_set"}
)
print(f"Set Procedure Run Info: {procedure_run.get_info()}")

# Check if procedure run exists before deletion
exists = ProcedureRun.exists(
    procedure_run_info={"test": "test"}
)
print(f"Procedure Run exists: {exists}")

# Delete the created procedure run
is_deleted = new_procedure_run.delete()
print(f"Deleted Procedure Run: {is_deleted}")

# Check if procedure run exists after deletion
exists = ProcedureRun.exists(
    procedure_run_info={"test": "test"}
)
print(f"Procedure Run exists after deletion: {exists}")
```

## Explanation

This example demonstrates the basic operations for managing procedure runs using the GEMINIbase API:

*   **Creating a procedure run:** The `ProcedureRun.create()` method is used to create a new procedure run with additional information.
*   **Getting a procedure run:** The `ProcedureRun.get()` method retrieves a procedure run by its additional information. The `ProcedureRun.get_by_id()` method retrieves a procedure run by its unique ID.
*   **Getting all procedure runs:** The `ProcedureRun.get_all()` method retrieves all procedure runs in the database.
*   **Searching for procedure runs:** The `ProcedureRun.search()` method finds procedure runs based on specified criteria, such as the additional information.
*   **Refreshing a procedure run:** The `ProcedureRun.refresh()` method updates the procedure run object with the latest data from the database.
*   **Updating a procedure run:** The `ProcedureRun.update()` method updates the attributes of an existing procedure run.
*   **Setting procedure run information:** The `ProcedureRun.set_info()` method updates the `procedure_run_info` field with new data.
*   **Checking for existence:** The `ProcedureRun.exists()` method verifies if a procedure run with the given attributes exists.
*   **Deleting a procedure run:** The `ProcedureRun.delete()` method removes the procedure run from the database.
