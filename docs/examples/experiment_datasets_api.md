# Experiment Datasets API Example

This example demonstrates how to associate and unassociate datasets with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_datasets_api.py`.

## Code

```python
from gemini.api.experiment import Experiment
from gemini.api.dataset import Dataset

# Create a new dataset for Experiment A
new_dataset = Dataset.create(
    dataset_name="New Dataset",
    dataset_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Dataset: {new_dataset}")

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new dataset
experiment_b.associate_dataset(dataset_name=new_dataset.dataset_name)
print(f"Associated New Dataset with Experiment B: {experiment_b}")

# Get Associated Datasets
associated_datasets = experiment_b.get_associated_datasets()
for dataset in associated_datasets:
    print(f"Associated Dataset: {dataset}")

# Check if the new dataset is associated with Experiment B
is_associated = experiment_b.belongs_to_dataset(dataset_name=new_dataset.dataset_name)
print(f"Is New Dataset associated with Experiment B? {is_associated}")

# Unassociate the new dataset from Experiment B
experiment_b.unassociate_dataset(dataset_name=new_dataset.dataset_name)
print(f"Unassociated New Dataset from Experiment B: {experiment_b}")

# Check if the new dataset is still associated with Experiment B
is_associated = experiment_b.belongs_to_dataset(dataset_name=new_dataset.dataset_name)
print(f"Is New Dataset still associated with Experiment B? {is_associated}")

# Create a new dataset for Experiment B
experiment_dataset = experiment_b.create_new_dataset(
    dataset_name="Experiment B Dataset",
    dataset_info={"test": "test"}
)
print(f"Created New Dataset: {experiment_dataset}")
```

## Explanation

This example demonstrates how to manage the association between datasets and experiments:

*   **Creating a dataset:** A new dataset is created and associated with Experiment A.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment B in this case).
*   **Associating with a dataset:** The `associate_dataset()` method associates the experiment with the created dataset.
*   **Getting associated datasets:** The `get_associated_datasets()` method retrieves a list of datasets associated with the experiment.
*   **Checking association:** The `belongs_to_dataset()` method verifies if the experiment is associated with a specific dataset.
*   **Unassociating from a dataset:** The `unassociate_dataset()` method removes the association between the experiment and the dataset.
*   **Verifying unassociation:** The `belongs_to_dataset()` method is used again to confirm that the experiment is no longer associated with the dataset.
*   **Creating a new dataset for an experiment:** The `create_new_dataset()` method creates a new dataset and automatically associates it with the experiment.
