# Trait Dataset API Example

This example demonstrates how to use the Trait and Dataset APIs to associate datasets with traits in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/trait_dataset_api.py`.

## Code

```python
from gemini.api.trait import Trait
from gemini.api.dataset import Dataset, GEMINIDatasetType

# Create a new trait for Experiment A
new_trait = Trait.create(
    trait_name="Trait Test 1",
    trait_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Trait: {new_trait}")

# Create a new dataset for Experiment A
new_dataset = Dataset.create(
    dataset_name="Dataset Trait Test 1",
    dataset_type=GEMINIDatasetType.Trait,
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset: {new_dataset}")

# Create a new Dataset for New Trait directly
new_trait_dataset = new_trait.create_new_dataset(
    dataset_name="Trait Test 1 Dataset",
    dataset_info={"test": "test"},
    collection_date="2023-10-01",
    experiment_name="Experiment A"
)
print(f"Created New Dataset for New Trait: {new_trait_dataset}")

# Associate the new dataset with the new trait
new_trait.associate_dataset(dataset_name=new_dataset.dataset_name)
print(f"Associated New Dataset with New Trait: {new_trait}")

# Print the associated datasets
associated_datasets = new_trait.get_associated_datasets()
for dataset in associated_datasets:
    print(f"Associated Dataset: {dataset}")
```

## Explanation

This example demonstrates how to manage the association between datasets and traits:

*   **Creating a trait:** The `Trait.create()` method is used to create a new trait with a name, additional information, and associated experiment.
*   **Creating a dataset:** The `Dataset.create()` method is used to create a new dataset with a name, type, additional information, collection date, and associated experiment.
*   **Creating a dataset for a trait:** The `Trait.create_new_dataset()` method is used to create a new dataset and automatically associate it with the trait.
*   **Associating with a dataset:** The `associate_dataset()` method associates the trait with the created dataset.
*   **Getting associated datasets:** The `get_associated_datasets()` method retrieves a list of datasets associated with the trait.
