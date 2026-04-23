# Dataset Experiment API Example

This example demonstrates how to associate and unassociate datasets with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/dataset_experiment_api.py`.

## Code

```python
from gemini.api.dataset import Dataset, GEMINIDatasetType

# Create a new dataset for Experiment A
new_dataset = Dataset.create(
    dataset_name="Test Dataset",
    dataset_type=GEMINIDatasetType.Sensor,
    dataset_info={
        "description": "This is a test dataset for API demonstration.",
        "version": "1.0",
    },
    experiment_name="Experiment A",
    collection_date="2023-10-01"
)
print(f"Created Dataset: {new_dataset}")

# Get associated experiments for the dataset
associated_experiments = new_dataset.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the dataset with Experiment B
new_dataset.associate_experiment(experiment_name="Experiment B")
print(f"Associated dataset {new_dataset.dataset_name} with Experiment B")

# Check if the dataset is associated with Experiment B
is_associated = new_dataset.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is dataset {new_dataset.dataset_name} associated with Experiment B? {is_associated}")

# Unassociate the dataset from Experiment B
new_dataset.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated dataset {new_dataset.dataset_name} from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_dataset.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is dataset {new_dataset.dataset_name} still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between datasets and experiments:

*   **Creating a dataset:** A new dataset is created and associated with Experiment A.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the dataset.
*   **Associating with an experiment:** The `associate_experiment()` method associates the dataset with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the dataset is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the dataset and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the dataset is no longer associated with Experiment B.
