# Procedure Experiment API Example

This example demonstrates how to associate and unassociate experiments with procedures using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/procedure_experiment_api.py`.

## Code

```python
from gemini.api.procedure import Procedure

# Create a new procedure for Experiment A
new_procedure = Procedure.create(
    procedure_name="Procedure Test 1",
    procedure_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Procedure: {new_procedure}")

# Get associated experiments
associated_experiments = new_procedure.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the procedure with Experiment B
new_procedure.associate_experiment(experiment_name="Experiment B")
print(f"Associated Procedure with Experiment B")

# Check if the procedure is associated with Experiment B
is_associated = new_procedure.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Procedure associated with Experiment B? {is_associated}")

# Unassociate the procedure from Experiment B
new_procedure.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Procedure from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_procedure.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Procedure still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between experiments and procedures:

*   **Creating a procedure:** The `Procedure.create()` method is used to create a new procedure with a name and additional information.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the procedure.
*   **Associating with an experiment:** The `associate_experiment()` method associates the procedure with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the procedure is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the procedure and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the procedure is no longer associated with Experiment B.
