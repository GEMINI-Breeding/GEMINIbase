# Model Dataset API Example

This example demonstrates how to use the Model and Dataset APIs to associate datasets with models in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/model_dataset_api.py`.

## Code

```python
from gemini.api.model import Model
from gemini.api.dataset import Dataset, GEMINIDatasetType

# Create a new model for Experiment A
new_model = Model.create(
    model_name="Model Test 1",
    model_url="https://example.com/model_test_1",
    model_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Model: {new_model}")

# Create a new Dataset for Experiment A
new_dataset = Dataset.create(
    dataset_name="Dataset Test 1",
    dataset_type=GEMINIDatasetType.Model,
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset: {new_dataset}")

# Create a new Dataset for New Model directly
new_model_dataset = new_model.create_new_dataset(
    dataset_name="Model Test 1 Dataset",
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset for New Model: {new_model_dataset}")

# Associate the new dataset with the new model
new_model.associate_dataset(dataset_name=new_dataset.dataset_name)
print(f"Associated New Dataset with New Model: {new_model}")

# Print the associated datasets
associated_datasets = new_model.get_associated_datasets()
for dataset in associated_datasets:
    print(f"Associated Dataset: {dataset}")
```

## Explanation

This example demonstrates how to manage the association between datasets and models:

*   **Creating a model:** The `Model.create()` method is used to create a new model with a name, URL, additional information, and associated experiment.
*   **Creating a dataset:** The `Dataset.create()` method is used to create a new dataset with a name, type, additional information, collection date, and associated experiment.
*   **Creating a dataset for a model:** The `Model.create_new_dataset()` method is used to create a new dataset and automatically associate it with the model.
*   **Associating with a dataset:** The `associate_dataset()` method associates the model with the created dataset.
*   **Getting associated datasets:** The `get_associated_datasets()` method retrieves a list of datasets associated with the model.
