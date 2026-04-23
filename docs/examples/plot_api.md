# Plot API Example

This example demonstrates how to use the Plot API in the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/plot_api.py`.

## Code

```python
from gemini.api.plot import Plot

# Create a new plot
new_plot = Plot.create(
    plot_number=1000,
    plot_row_number=1,
    plot_column_number=1,
    plot_info={"test": "test"},
    plot_geometry_info={"test": "test"},
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1",
    accession_name="Accession A1",
    population_name="Population A"
)
print(f"Created New Plot: {new_plot}")

# Get Plot by ID
plot_by_id = Plot.get_by_id(new_plot.id)
print(f"Got Plot by ID: {plot_by_id}")

# Get Plot
plot = Plot.get(
    plot_number=new_plot.plot_number,
    plot_row_number=1,
    plot_column_number=1,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Got Plot: {plot}")

# Get all plots
all_plots = Plot.get_all()
print(f"All Plots:")
for p in all_plots[:10]:  # Limit to first 10 plots for display
    print(p)

# Search for plots in Experiment A
searched_plots = Plot.search(experiment_name="Experiment A")
length_searched_plots = len(searched_plots)
print(f"Found {length_searched_plots} plots in Experiment A")

# Refresh the plot
plot.refresh()
print(f"Refreshed Plot: {plot}")

# Update the plot
plot.update(
    plot_number=2000,
    plot_row_number=2,
    plot_column_number=2,
    plot_info={"updated": "info"},
    plot_geometry_info={"updated": "info"}
)
print(f"Updated Plot: {plot}")

# Set Plot Info
plot.set_info(plot_info={"new": "info"})
print(f"Set Plot Info: {plot.get_info()}")

# Check if the plot exists
exists = Plot.exists(
    plot_number=2000,
    plot_row_number=2,
    plot_column_number=2,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Plot exists: {exists}")

# Delete the created plot
is_deleted = new_plot.delete()
print(f"Deleted Plot: {is_deleted}")

# Check if the plot exists after deletion
exists_after_deletion = Plot.exists(
    plot_number=2000,
    plot_row_number=2,
    plot_column_number=2,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Plot exists after deletion: {exists_after_deletion}")
```

## Explanation

This example demonstrates the basic operations for managing plots using the GEMINIbase API:

*   **Creating a plot:** The `Plot.create()` method is used to create a new plot with a plot number, row number, column number, additional information, geometry information, and associated experiment, season, site, and population.
*   **Getting a plot:** The `Plot.get_by_id()` method retrieves a plot by its unique ID. The `Plot.get()` method retrieves a plot by its plot number, row number, column number, and associated experiment, season, and site.
*   **Getting all plots:** The `Plot.get_all()` method retrieves all plots in the database.
*   **Searching for plots:** The `Plot.search()` method finds plots based on specified criteria, such as the experiment name.
*   **Refreshing a plot:** The `Plot.refresh()` method updates the plot object with the latest data from the database.
*   **Updating a plot:** The `Plot.update()` method updates the attributes of an existing plot.
*   **Setting plot information:** The `Plot.set_info()` method updates the `plot_info` field with new data.
*   **Checking for existence:** The `Plot.exists()` method verifies if a plot with the given attributes exists.
*   **Deleting a plot:** The `Plot.delete()` method removes the plot from the database.
