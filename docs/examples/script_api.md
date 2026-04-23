# Script API Example

This example demonstrates how to use the Script API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/script_api.py`.

## Code

```python
from gemini.api.script import Script

# Create a new script for Experiment A
new_script = Script.create(
    script_name="Script Test 1",
    script_url="https://example.com/script_test_1",
    script_extension="py",
    script_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Script: {new_script}")

# Get Script by ID
script_from_id = Script.get(new_script.id)
print(f"Got Script from ID: {script_from_id}")

# Get Script by Name
script_from_name = Script.get(script_name="Script Test 1")
print(f"Got Script from Name: {script_from_name}")

# Get all scripts
all_scripts = Script.get_all()
for script in all_scripts:
    print(f"Script: {script}")

# Search for scripts by name
search_results = Script.search(script_name="Script Test 1")
for result in search_results:
    print(f"Search Result: {result}")

# Update Script
script_from_name.update(
    script_url="https://example.com/updated_script_test_1",
    script_info={"updated": "info"}
)
print(f"Updated Script: {script_from_name}")

# Refresh Script
script_from_name.refresh()
print(f"Refreshed Script: {script_from_name}")

# Set Script Info
script_from_name.set_info(
    script_info={"new": "info"}
)
print(f"Set Script Info: {script_from_name.get_info()}")

# Check if Script Exists
exists = Script.exists(script_name="Script Test 1")
print(f"Does Script Exist? {exists}")

# Delete Script
is_deleted = script_from_name.delete()
print(f"Deleted Script: {is_deleted}")

# Check if Script Exists after Deletion
exists_after_deletion = Script.exists(script_name="Script Test 1")
print(f"Does Script Exist after Deletion? {exists_after_deletion}")

# Delete Script
is_deleted = new_script.delete()
print(f"Deleted Script: {is_deleted}")

# Check if Script Exists after Deletion
exists_after_deletion = Script.exists(script_name="Script Test 1")
print(f"Does Script Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing scripts using the GEMINIbase API:

*   **Creating a script:** The `Script.create()` method is used to create a new script with a name, URL, extension, additional information, and associated experiment.
*   **Getting a script:** The `Script.get()` method retrieves a script by its ID or name.
*   **Getting all scripts:** The `Script.get_all()` method retrieves all scripts in the database.
*   **Searching for scripts:** The `Script.search()` method finds scripts based on specified criteria, such as the name.
*   **Updating a script:** The `Script.update()` method updates the attributes of an existing script.
*   **Refreshing a script:** The `Script.refresh()` method updates the script object with the latest data from the database.
*   **Setting script information:** The `Script.set_info()` method updates the `script_info` field with new data.
*   **Checking for existence:** The `Script.exists()` method verifies if a script with the given name exists.
*   **Deleting a script:** The `Script.delete()` method removes the script from the database.
