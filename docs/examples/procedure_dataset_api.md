# Procedure Dataset API Example

This example demonstrates how to use the Procedure and Dataset APIs to associate datasets with procedures in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/procedure_dataset_api.py`.

## Code

```python
from gemini.api.procedure import Procedure
from gemini.api.dataset import Dataset, GEMINIDatasetType

# Create a new procedure for Experiment A
new_procedure = Procedure.create(
    procedure_name="Procedure Test 1",
    procedure_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Procedure: {new_procedure}")

# Create a new Dataset for Experiment A
new_dataset = Dataset.create(
    dataset_name="Dataset Test 1",
    dataset_type=GEMINIDatasetType.Procedure,
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset: {new_dataset}")

# Create a new Dataset for New Procedure directly
new_procedure_dataset = new_procedure.create_new_dataset(
    dataset_name="Procedure Test 1 Dataset",
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset for New Procedure: {new_procedure_dataset}")

# Associate the new dataset with the new procedure
new_procedure.associate_dataset(dataset_name=new_dataset.dataset_name)
print(f"Associated New Dataset with New Procedure: {new_procedure}")

# Print the associated datasets
associated_datasets = new_procedure.get_associated_datasets()
for dataset in associated_datasets:
    print(f"Associated Dataset: {dataset}")
```

## Explanation

This example demonstrates how to manage the association between datasets and procedures:

*   **Creating a procedure:** The `Procedure.create()` method is used to create a new procedure with a name and additional information.
*   **Creating a dataset:** The `Dataset.create()` method is used to create a new dataset with a name, type, additional information, collection date, and associated experiment.
*   **Creating a dataset for a procedure:** The `Procedure.create_new_dataset()` method is used to create a new dataset and automatically associate it with the procedure.
*   **Associating with a dataset:** The `associate_dataset()` method associates the procedure with the created dataset.
*   **Getting associated datasets:** The `get_associated_datasets()` method retrieves a list of datasets associated with the procedure.
