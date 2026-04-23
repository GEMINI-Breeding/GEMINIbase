# Experiment Script API Example

This example demonstrates how to associate and unassociate scripts with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_script_api.py`.

## Code

```python
from gemini.api.experiment import Experiment
from gemini.api.script import Script

# Create a new script for Experiment A
new_script = Script.create(
    script_name="New Script",
    script_url="gs://gemini-scripts/new_script.py",
    script_extension="py",
    script_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Script: {new_script}")

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new script
experiment_b.associate_script(script_name=new_script.script_name)
print(f"Associated New Script with Experiment B: {experiment_b}")

# Get Associated Scripts
associated_scripts = experiment_b.get_associated_scripts()
for script in associated_scripts:
    print(f"Associated Script: {script}")

# Check if the new script is associated with Experiment B
is_associated = experiment_b.belongs_to_script(script_name=new_script.script_name)
print(f"Is New Script associated with Experiment B? {is_associated}")

# Unassociate the new script from Experiment B
experiment_b.unassociate_script(script_name=new_script.script_name)
print(f"Unassociated New Script from Experiment B: {experiment_b}")

# Check if the new script is still associated with Experiment B
is_associated = experiment_b.belongs_to_script(script_name=new_script.script_name)
print(f"Is New Script still associated with Experiment B? {is_associated}")

# Create a new script for Experiment B
experiment_script = experiment_b.create_new_script(
    script_name="Experiment B Script",
    script_url="gs://gemini-scripts/experiment_b_script.py",
    script_extension="py",
    script_info={"test": "test"}
)
print(f"Created New Script: {experiment_script}")
```

## Explanation

This example demonstrates how to manage the association between scripts and experiments:

*   **Creating a script:** A new script is created and associated with Experiment A.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment B in this case).
*   **Associating with a script:** The `associate_script()` method associates the experiment with the created script.
*   **Getting associated scripts:** The `get_associated_scripts()` method retrieves a list of scripts associated with the experiment.
*   **Checking association:** The `belongs_to_script()` method verifies if the experiment is associated with a specific script.
*   **Unassociating from a script:** The `unassociate_script()` method removes the association between the experiment and the script.
*   **Verifying unassociation:** The `belongs_to_script()` method is used again to confirm that the experiment is no longer associated with the script.
*   **Creating a new script for an experiment:** The `create_new_script()` method creates a new script and automatically associates it with the experiment.
