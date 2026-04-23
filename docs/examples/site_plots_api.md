# Site Plots API Example

This example demonstrates how to associate and unassociate plots with sites using the GEMINIbase.

## Source File Location

The original Python script is located at `gemini/examples/api/site_plots_api.py`.

## Code

```python
from gemini.api.site import Site
from gemini.api.experiment import Experiment
from gemini.api.plot import Plot

# Create a new Plot for Experiment A and Site A1
new_plot = Plot.create(
    plot_number=1011,
    plot_row_number=1011,
    plot_column_number=1011,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Created New Plot: {new_plot}")

# Get Site A2
site_a2 = Site.get("Site A2")
print(f"Got Site A2: {site_a2}")

# Create a new plot for Site A2 explicitly
site_a2.create_new_plot(
    plot_number=2022,
    plot_row_number=2022,
    plot_column_number=2022,
    season_name="Season 1A",
    experiment_name="Experiment A"
)

# Associate Site A2 with the new plot
site_a2.associate_plot(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    season_name=new_plot.season_name,
    experiment_name=new_plot.experiment_name
)
print(f"Associated New Plot with Site A2: {site_a2}")

# Get Associated Plots
associated_plots = site_a2.get_associated_plots()
for plot in associated_plots:
    print(f"Associated Plot: {plot}")

# Check if the new plot is associated with Site A2
is_associated = site_a2.belongs_to_plot(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    season_name=new_plot.season_name,
    experiment_name=new_plot.experiment_name
)
print(f"Is New Plot associated with Site A2? {is_associated}")

# Unassociate the new plot from Site A2
site_a2.unassociate_plot(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    season_name=new_plot.season_name,
    experiment_name=new_plot.experiment_name
)
print(f"Unassociated New Plot from Site A2: {site_a2}")

# Check if the new plot is still associated with Site A2
is_associated = site_a2.belongs_to_plot(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    season_name=new_plot.season_name,
    experiment_name=new_plot.experiment_name
)
print(f"Is New Plot still associated with Site A2? {is_associated}")
```

## Explanation

This example demonstrates how to manage the association between plots and sites:

*   **Creating a plot:** The `Plot.create()` method is used to create a new plot with plot information, additional information, and associated experiment, season, and site.
*   **Getting a site:** The `Site.get()` method retrieves a site by its name.
*   **Creating a new plot for a site:** The `create_new_plot()` method creates a new plot and automatically associates it with the site.
*   **Associating with a plot:** The `associate_plot()` method associates the site with the created plot.
*   **Getting associated plots:** The `get_associated_plots()` method retrieves a list of plots associated with the site.
*   **Checking association:** The `belongs_to_plot()` method verifies if the site is associated with a specific plot.
*   **Unassociating from a plot:** The `unassociate_plot()` method removes the association between the site and the plot.
*   **Verifying unassociation:** The `belongs_to_plot()` method is used again to confirm that the site is no longer associated with the plot.
