# Procedure Procedure Run API Example

This example demonstrates how to associate and create procedure runs with procedures using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/procedure_procedure_run_api.py`.

## Code

```python
from gemini.api.procedure import Procedure

# Get Procedure A
procedure_a = Procedure.get("Procedure A")
print(f"Got Procedure A: {procedure_a}")

# Create a new procedure run for Procedure A
new_procedure_a_run = procedure_a.create_new_run(
    procedure_run_info={"test": "test"}
)
print(f"Created New Procedure Run: {new_procedure_a_run}")

# Get Associated Procedure Runs
associated_procedure_runs = procedure_a.get_associated_runs()
for procedure_run in associated_procedure_runs:
    print(f"Associated Procedure Run: {procedure_run}")
```

## Explanation

This example demonstrates how to manage the association between procedure runs and procedures:

*   **Getting a procedure:** The `Procedure.get()` method retrieves a procedure by its name (Procedure A in this case).
*   **Creating a new procedure run:** The `create_new_run()` method creates a new procedure run and automatically associates it with the procedure.
*   **Getting associated procedure runs:** The `get_associated_runs()` method retrieves a list of procedure runs associated with the procedure.
