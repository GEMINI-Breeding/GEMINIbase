# Site Experiment API Example

This example demonstrates how to associate and unassociate experiments with sites using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/site_experiment_api.py`.

## Code

```python
from gemini.api.site import Site

# Create a new Site for Experiment A
new_site = Site.create(
    site_name="Site Test 1",
    site_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Site: {new_site}")

# Get associated experiments
associated_experiments = new_site.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the new site with Experiment B
new_site.associate_experiment(experiment_name="Experiment B")
print(f"Associated Site with Experiment B")

# Check if the new site is associated with Experiment B
is_associated = new_site.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Site associated with Experiment B? {is_associated}")

# Unassociate the new site from Experiment B
new_site.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Site from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_site.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Site still associated with Experiment B? {is_associated_after_unassociation}")
```

## Explanation

This example demonstrates how to manage the association between experiments and sites:

*   **Creating a site:** The `Site.create()` method is used to create a new site with a name, additional information, and associated experiment.
*   **Getting associated experiments:** The `get_associated_experiments()` method retrieves a list of experiments associated with the site.
*   **Associating with an experiment:** The `associate_experiment()` method associates the site with another experiment (Experiment B in this case).
*   **Checking association:** The `belongs_to_experiment()` method verifies if the site is associated with a specific experiment.
*   **Unassociating from an experiment:** The `unassociate_experiment()` method removes the association between the site and Experiment B.
*   **Verifying unassociation:** The `belongs_to_experiment()` method is used again to confirm that the site is no longer associated with Experiment B.
