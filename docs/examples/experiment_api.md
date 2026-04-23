# Experiment API Example

This example demonstrates how to use the Experiment API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_api.py`.

## Code

```python
from gemini.api.experiment import Experiment

# Create a new Experiment
new_experiment = Experiment.create(
    experiment_name="Experiment Test 1",
    experiment_info={"test": "test"},
    experiment_start_date="2023-10-01",
    experiment_end_date="2023-12-31"
)
print(f"Created Experiment: {new_experiment}")

# Get Experiment by name
experiment = Experiment.get("Experiment Test 1")
print(f"Got Experiment: {experiment}")

# Get Experiment by ID
experiment_by_id = Experiment.get_by_id(new_experiment.id)
print(f"Got Experiment by ID: {experiment_by_id}")

# Get all experiments
all_experiments = Experiment.get_all()
print(f"All Experiments:")
for exp in all_experiments:
    print(exp)

# Search for experiments
searched_experiments = Experiment.search(experiment_name="Experiment Test 1")
length_searched_experiments = len(searched_experiments)
print(f"Found {length_searched_experiments} experiments with name 'Experiment Test 1'")

# Update the experiment
experiment = experiment.update(
    experiment_info={"test": "updated test"},
    experiment_start_date="2023-10-02",
    experiment_end_date="2023-12-30"
)
print(f"Updated Experiment: {experiment}")

# Set experiment info
experiment.set_info(
    experiment_info={"test": "new test"}
)
print(f"Set Experiment Info: {experiment.get_info()}")

# Check if the experiment exists
experiment_exists = Experiment.exists(experiment_name="Experiment Test 1")
print(f"Does Experiment exist? {experiment_exists}")

# Delete the experiment
experiment.delete()
print(f"Deleted Experiment: {experiment}")

# Check if the experiment exists after deletion
experiment_exists_after_deletion = Experiment.exists(experiment_name="Experiment Test 1")
print(f"Does Experiment exist after deletion? {experiment_exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing experiments using the GEMINIbase API:

*   **Creating an experiment:** The `Experiment.create()` method is used to create a new experiment with a name, additional information, start date, and end date.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name. The `Experiment.get_by_id()` method retrieves an experiment by its unique ID.
*   **Getting all experiments:** The `Experiment.get_all()` method retrieves all experiments in the database.
*   **Searching for experiments:** The `Experiment.search()` method finds experiments based on specified criteria, such as the name.
*   **Updating an experiment:** The `Experiment.update()` method updates the attributes of an existing experiment.
*   **Setting experiment information:** The `Experiment.set_info()` method updates the `experiment_info` field with new data.
*   **Checking for existence:** The `Experiment.exists()` method verifies if an experiment with the given name exists.
*   **Deleting an experiment:** The `Experiment.delete()` method removes the experiment from the database.
