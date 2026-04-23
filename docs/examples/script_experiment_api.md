# Script Experiment API Example

This example demonstrates how to associate and unassociate experiments with scripts using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/script_experiment_api.py`.

## Code

```python
from gemini.api.script import Script

# Create a new script for Experiment A
new_script = Script.create(
    script_name="Script Test 1",
    script_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Script: {new_script}")

# Get associated experiments
associated_experiments = new_script.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the script with Experiment B
new_script.associate_experiment(experiment_name="Experiment B")
print(f"Associated Script with Experiment B")

# Check if the script is associated with Experiment B
is_associated = new_script.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Script associated with Experiment B? {is_associated}")

# Unassociate the script from Experiment B
new_script.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Script from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_script.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Script still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between experiments and scripts:

*   **Creating a script:** The `Script.create()` method is used to create a new script with a name, additional information, and associated experiment.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the script.
*   **Associating with an experiment:** The `associate_experiment()` method associates the script with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the script is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the script and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the script is no longer associated with Experiment B.
