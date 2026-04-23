# Script Run Script API Example

This example demonstrates how to associate and unassociate scripts with script runs using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/script_run_script_api.py`.

## Code

```python
from gemini.api.script import Script
from gemini.api.script_run import ScriptRun

# Create a new script run for Script A
new_script_run = ScriptRun.create(
    script_run_info={"test": "test"},
    script_name="Script A"
)
print(f"Created New Script Run: {new_script_run}")

# Create a new script for Experiment A
new_script = Script.create(
    script_name="Script  X",
    script_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Script: {new_script}")

# Get associated script of the new script run
associated_script = new_script_run.get_associated_script()
print(f"Associated Script: {associated_script}")

# Associate the new script run with the new script
new_script_run.associate_script(script_name=new_script.script_name)
print(f"Associated New Script Run with New Script: {new_script_run}")

# Check if the new script run is associated with the new script
is_associated = new_script_run.belongs_to_script(script_name=new_script.script_name)
print(f"Is New Script Run associated with New Script? {is_associated}")

# Unassociate the new script run from the new script
new_script_run.unassociate_script()
print(f"Unassociated New Script Run from New Script: {new_script_run}")

# Check if the new script run is still associated with the new script
is_associated = new_script_run.belongs_to_script(script_name=new_script.script_name)
print(f"Is New Script Run still associated with New Script? {is_associated}")
```

## Explanation

This example demonstrates how to manage the association between scripts and script runs:

*   **Creating a script run:** The `ScriptRun.create()` method is used to create a new script run with additional information and associated script.
*   **Creating a script:** The `Script.create()` method is used to create a new script.
*   **Getting associated script:** The `get_associated_script()` method retrieves the script associated with the script run.
*   **Associating with a script:** The `associate_script()` method associates the script run with the created script.
*   **Checking association:** The `belongs_to_script()` method verifies if the script run is associated with a specific script.
*   **Unassociating from a script:** The `unassociate_script()` method removes the association between the script run and the script.
*   **Verifying unassociation:** The `belongs_to_script()` method is used again to confirm that the script run is no longer associated with the script.
