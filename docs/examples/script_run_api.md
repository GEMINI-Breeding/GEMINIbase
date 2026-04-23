# Script Run API Example

This example demonstrates how to use the ScriptRun API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/script_run_api.py`.

## Code

```python
from gemini.api.script import Script
from gemini.api.script_run import ScriptRun

# Get script by name
script = Script.get("Script A")
print(f"Got Script: {script}")

# Create a new script run
script_run = ScriptRun.create(
    script_run_info={"test": "test"},
    script_name=script.script_name
)
print(f"Created Script Run: {script_run}")

# Get ScriptRun with script_run_info that does exist
script_run = ScriptRun.get(
    script_run_info={"test": "test"},
    script_name=script.script_name
)
print(f"Got ScriptRun: {script_run}")

# Get ScriptRun by ID
script_run = ScriptRun.get_by_id(script_run.id)
print(f"Got ScriptRun by ID: {script_run}")

# Get all script runs
all_script_runs = ScriptRun.get_all()
print(f"All Script Runs:")
for script_run in all_script_runs:
    print(script_run)

# Search for script runs
searched_script_runs = ScriptRun.search(script_name=script.script_name)
length_searched_script_runs = len(searched_script_runs)
print(f"Found {length_searched_script_runs} script runs")

# Refresh the script run
script_run.refresh()
print(f"Refreshed Script Run: {script_run}")

# Update the script run
script_run.update(
    script_run_info={"test": "test_updated"},
)
print(f"Updated Script Run: {script_run}")

# Set ScriptRun Info
script_run.set_info(
    script_run_info={"test": "test_set"},
)
print(f"Set ScriptRun Info: {script_run.get_info()}")

# Check if ScriptRun exists before deletion
exists = ScriptRun.exists(script_run_info={"test": "test_set"}, script_name=script.script_name)
print(f"ScriptRun exists before deletion: {exists}")

# Delete the script run
is_deleted = script_run.delete()
print(f"Deleted Script Run: {is_deleted}")

# Check if ScriptRun exists after deletion
exists = ScriptRun.exists(script_run_info={"test": "test_set"}, script_name=script.script_name)
print(f"ScriptRun exists after deletion: {exists}")
```

## Explanation

This example demonstrates the basic operations for managing script runs using the GEMINIbase API:

*   **Getting a script:** The `Script.get()` method retrieves a script by its name.
*   **Creating a script run:** The `ScriptRun.create()` method is used to create a new script run with additional information and associated script.
*   **Getting a script run:** The `ScriptRun.get()` method retrieves a script run by its additional information and script name. The `ScriptRun.get_by_id()` method retrieves a script run by its unique ID.
*   **Getting all script runs:** The `ScriptRun.get_all()` method retrieves all script runs in the database.
*   **Searching for script runs:** The `ScriptRun.search()` method finds script runs based on specified criteria, such as the script name.
*   **Refreshing a script run:** The `ScriptRun.refresh()` method updates the script run object with the latest data from the database.
*   **Updating a script run:** The `ScriptRun.update()` method updates the attributes of an existing script run.
*   **Setting script run information:** The `ScriptRun.set_info()` method updates the `script_run_info` field with new data.
*   **Checking for existence:** The `ScriptRun.exists()` method verifies if a script run with the given attributes exists.
*   **Deleting a script run:** The `ScriptRun.delete()` method removes the script run from the database.
