# Site API Example

This example demonstrates how to use the Site API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/site_api.py`.

## Code

```python
from gemini.api.site import Site

# Create a new Site for Experiment A
new_site = Site.create(
    site_name="Site A",
    site_info={"location": "Field 1"},
    experiment_name="Experiment A"
)
print(f"Created New Site: {new_site}")

# Get Site by ID
site_by_id = Site.get_by_id(new_site.id)
print(f"Got Site by ID: {site_by_id}")

# Get Site by Name
site_by_name = Site.get(site_name="Site A")
print(f"Got Site by Name: {site_by_name}")

# Get all Sites
all_sites = Site.get_all()
for site in all_sites:
    print(f"Site: {site}")

# Search for Sites by Name
search_results = Site.search(site_name="Site A")
for result in search_results:
    print(f"Search Result: {result}")

# Update Site
site_by_name.update(
    site_info={"location": "Field 2"}
)
print(f"Updated Site: {site_by_name}")

# Refresh Site
site_by_name.refresh()
print(f"Refreshed Site: {site_by_name}")

# Set Site Info
site_by_name.set_info(
    site_info={"new_location": "Field 3"}
)
print(f"Set Site Info: {site_by_name.get_info()}")

# Check if Site Exists
exists = Site.exists(site_name="Site A")
print(f"Does Site Exist? {exists}")

# Delete Site
is_deleted = site_by_name.delete()
print(f"Deleted Site: {is_deleted}")

# Check if Site Exists after Deletion
exists_after_deletion = Site.exists(site_name="Site A")
print(f"Does Site Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing sites using the GEMINIbase API:

*   **Creating a site:** The `Site.create()` method is used to create a new site with a name, additional information, and associated experiment.
*   **Getting a site:** The `Site.get_by_id()` method retrieves a site by its unique ID. The `Site.get()` method retrieves a site by its name.
*   **Getting all sites:** The `Site.get_all()` method retrieves all sites in the database.
*   **Searching for sites:** The `Site.search()` method finds sites based on specified criteria, such as the name.
*   **Updating a site:** The `Site.update()` method updates the attributes of an existing site.
*   **Refreshing a site:** The `Site.refresh()` method updates the site object with the latest data from the database.
*   **Setting site information:** The `Site.set_info()` method updates the `site_info` field with new data.
*   **Checking for existence:** The `Site.exists()` method verifies if a site with the given name exists.
*   **Deleting a site:** The `Site.delete()` method removes the site from the database.
