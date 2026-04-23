# Experiment Season API Example

This example demonstrates how to associate and create seasons with experiments using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/experiment_season_api.py`.

## Code

```python
from gemini.api.experiment import Experiment

# Get Experiment A
experiment_a = Experiment.get("Experiment A")
print(f"Got Experiment A: {experiment_a}")

# Get Associated Seasons
associated_seasons = experiment_a.get_associated_seasons()
for season in associated_seasons:
    print(f"Associated Season: {season}")

# Create a new season for Experiment A
new_experiment_season = experiment_a.create_new_season(
    season_name="Experiment A Season 1",
    season_info={"test": "test"},
    season_start_date="2023-10-01",
    season_end_date="2023-12-31"
)
print(f"Created New Season: {new_experiment_season}")

# Get Associated Seasons for Experiment A
associated_seasons = experiment_a.get_associated_seasons()
for season in associated_seasons:
    print(f"Associated Season: {season}")
```

## Explanation

This example demonstrates how to manage the association between seasons and experiments:

*   **Getting an experiment:** The `Experiment.get()` method retrieves an experiment by its name (Experiment A in this case).
*   **Getting associated seasons:** The `get_associated_seasons()` method retrieves a list of seasons associated with the experiment.
*   **Creating a new season for an experiment:** The `create_new_season()` method creates a new season and automatically associates it with the experiment.
*   **Getting associated seasons after creation:** The `get_associated_seasons()` method is used again to confirm that the new season is associated with the experiment.
