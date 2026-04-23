# Season API Example

This example demonstrates how to use the Season API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/season_api.py`.

## Code

```python
from gemini.api.season import Season

# Create a new Season for Experiment A
new_season = Season.create(
    season_name="Season 1A",
    season_year=2024,
    season_info={"notes": "First season of Experiment A"},
    experiment_name="Experiment A"
)
print(f"Created New Season: {new_season}")

# Get Season by ID
season_by_id = Season.get_by_id(new_season.id)
print(f"Got Season by ID: {season_by_id}")

# Get Season by Name
season_by_name = Season.get(season_name="Season 1A")
print(f"Got Season by Name: {season_by_name}")

# Get all Seasons
all_seasons = Season.get_all()
for season in all_seasons:
    print(f"Season: {season}")

# Search for Seasons by Name
search_results = Season.search(season_name="Season 1A")
for result in search_results:
    print(f"Search Result: {result}")

# Update Season
season_by_name.update(
    season_year=2025
)
print(f"Updated Season: {season_by_name}")

# Refresh Season
season_by_name.refresh()
print(f"Refreshed Season: {season_by_name}")

# Set Season Info
season_by_name.set_info(
    season_info={"notes": "Updated notes for Season 1A"}
)
print(f"Set Season Info: {season_by_name.get_info()}")

# Check if Season Exists
exists = Season.exists(season_name="Season 1A")
print(f"Does Season Exist? {exists}")

# Delete Season
is_deleted = season_by_name.delete()
print(f"Deleted Season: {is_deleted}")

# Check if Season Exists after Deletion
exists_after_deletion = Season.exists(season_name="Season 1A")
print(f"Does Season Exist after Deletion? {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing seasons using the GEMINIbase API:

*   **Creating a season:** The `Season.create()` method is used to create a new season with a name, year, additional information, and associated experiment.
*   **Getting a season:** The `Season.get_by_id()` method retrieves a season by its unique ID. The `Season.get()` method retrieves a season by its name.
*   **Getting all seasons:** The `Season.get_all()` method retrieves all seasons in the database.
*   **Searching for seasons:** The `Season.search()` method finds seasons based on specified criteria, such as the name.
*   **Updating a season:** The `Season.update()` method updates the attributes of an existing season.
*   **Refreshing a season:** The `Season.refresh()` method updates the season object with the latest data from the database.
*   **Setting season information:** The `Season.set_info()` method updates the `season_info` field with new data.
*   **Checking for existence:** The `Season.exists()` method verifies if a season with the given name exists.
*   **Deleting a season:** The `Season.delete()` method removes the season from the database.
