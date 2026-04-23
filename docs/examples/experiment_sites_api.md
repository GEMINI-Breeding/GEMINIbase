# Experiment Sites API Example

This example demonstrates how to associate and unassociate sites with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_sites_api.py`.

## Code

```python
from gemini.api.experiment import Experiment
from gemini.api.site import Site

# Create a new site for Experiment A
new_site = Site.create(
    site_name="New Site",
    site_city="New City",
    site_state="New State",
    site_country="New Country",
    site_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created New Site: {new_site}")

# Get Experiment B
experiment_b = Experiment.get("Experiment B")
print(f"Got Experiment B: {experiment_b}")

# Associate Experiment B with the new site
experiment_b.associate_site(site_name=new_site.site_name)
print(f"Associated New Site with Experiment B: {experiment_b}")

# Get Associated Sites
associated_sites = experiment_b.get_associated_sites()
for site in associated_sites:
    print(f"Associated Site: {site}")

# Check if the new site is associated with Experiment B
is_associated = experiment_b.belongs_to_site(site_name=new_site.site_name)
print(f"Is New Site associated with Experiment B? {is_associated}")

# Unassociate the new site from Experiment B
experiment_b.unassociate_site(site_name=new_site.site_name)
print(f"Unassociated New Site from Experiment B: {experiment_b}")

# Check if the new site is still associated with Experiment B
is_associated = experiment_b.belongs_to_site(site_name=new_site.site_name)
print(f"Is New Site still associated with Experiment B? {is_associated}")

# Create a new site for Experiment B
experiment_site = experiment_b.create_new_site(
    site_name="Experiment B Site",
    site_city="Experiment B City",
    site_state="Experiment B State",
    site_country="Experiment B Country",
    site_info={"test": "test"}
)
print(f"Created New Site: {experiment_site}")
```

## Explanation

This example demonstrates how to manage the association between sites and experiments:

*   **Creating a site:** A new site is created and associated with Experiment A.
*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment B in this case).
*   **Associating with a site:** The `associate_site()` method associates the experiment with the created site.
*   **Getting associated sites:** The `get_associated_sites()` method retrieves a list of sites associated with the experiment.
*   **Checking association:** The `belongs_to_site()` method verifies if the experiment is associated with a specific site.
*   **Unassociating from a site:** The `unassociate_site()` method removes the association between the experiment and the site.
*   **Verifying unassociation:** The `belongs_to_site()` method is used again to confirm that the experiment is no longer associated with the site.
*   **Creating a new site for an experiment:** The `create_new_site()` method creates a new site and automatically associates it with the experiment.
