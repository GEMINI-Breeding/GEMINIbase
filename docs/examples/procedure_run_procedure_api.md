# Procedure Run Procedure API Example

This example demonstrates how to associate and unassociate procedures with procedure runs using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/procedure_run_procedure_api.py`.

## Code

```python
from gemini.api.procedure import Procedure
from gemini.api.procedure_run import ProcedureRun

# Create a new procedure run for Procedure A
new_procedure_run = ProcedureRun.create(
    procedure_run_info={"test": "test"},
    procedure_name="Procedure A"
)
print(f"Created New Procedure Run: {new_procedure_run}")

# Create a new procedure for Experiment A
new_procedure = Procedure.create(
    procedure_name="Procedure X",
    procedure_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Procedure: {new_procedure}")

# Get associated procedure of the new procedure run
associated_procedure = new_procedure_run.get_associated_procedure()
print(f"Associated Procedure: {associated_procedure}")

# Associate the new procedure run with the new procedure
new_procedure_run.associate_procedure(procedure_name=new_procedure.procedure_name)
print(f"Associated New Procedure Run with New Procedure: {new_procedure_run}")

# Check if the new procedure run is associated with the new procedure
is_associated = new_procedure_run.belongs_to_procedure(procedure_name=new_procedure.procedure_name)
print(f"Is New Procedure Run associated with New Procedure? {is_associated}")

# Unassociate the new procedure run from the new procedure
new_procedure_run.unassociate_procedure()
print(f"Unassociated New Procedure Run from New Procedure: {new_procedure_run}")

# Check if the new procedure run is still associated with the new procedure
is_associated = new_procedure_run.belongs_to_procedure(procedure_name=new_procedure.procedure_name)
print(f"Is New Procedure Run still associated with New Procedure? {is_associated}")
```

## Explanation

This example demonstrates how to manage the association between procedures and procedure runs:

*   **Creating a procedure run:** The `ProcedureRun.create()` method is used to create a new procedure run with additional information and associated procedure.
*   **Creating a procedure:** The `Procedure.create()` method is used to create a new procedure.
*   **Getting associated procedure:** The `get_associated_procedure()` method retrieves the procedure associated with the procedure run.
*   **Associating with a procedure:** The `associate_procedure()` method associates the procedure run with the created procedure.
*   **Checking association:** The `belongs_to_procedure()` method verifies if the procedure run is associated with a specific procedure.
*   **Unassociating from a procedure:** The `unassociate_procedure()` method removes the association between the procedure run and the procedure.
*   **Verifying unassociation:** The `belongs_to_procedure()` method is used again to confirm that the procedure run is no longer associated with the procedure.
