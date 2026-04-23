# Script Script Run API Example

This example demonstrates how to associate and create script runs with scripts using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/script_script_run_api.py`.

## Code

```python
from gemini.api.script import Script

# Get Script A
script_a = Script.get("Script A")
print(f"Got Script A: {script_a}")

# Create a new script run for Script A
new_script_a_run = script_a.create_new_run(
    script_run_info={"test": "test"}
)
print(f"Created New Script Run: {new_script_a_run}")

# Get Associated Script Runs
associated_script_runs = script_a.get_associated_runs()
for script_run in associated_script_runs:
    print(f"Associated Script Run: {script_run}")
```

## Explanation

This example demonstrates how to manage the association between script runs and scripts:

*   **Getting a script:** The `Script.get()` method retrieves a script by its name (Script A in this case).
*   **Creating a new script run:** The `create_new_run()` method creates a new script run and automatically associates it with the script.
*   **Getting associated script runs:** The `get_associated_runs()` method retrieves a list of script runs associated with the script.
