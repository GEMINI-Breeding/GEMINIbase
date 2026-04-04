# Plant Plot API Example

This example demonstrates how to associate and unassociate plots with plants using the Gemini framework.

## Source File Location

The original Python script is located at `gemini/examples/api/plant_plot_api.py`.

## Code

```python
from gemini.api.plant import Plant
from gemini.api.plot import Plot

new_plant = Plant.create(
    plant_number=7777,
    plant_info={
        "test": "test"
    },
)
print(f"Created New Plant: {new_plant}")

# Create a new Plot
new_plot = Plot.create(
    plot_number=1000,
    plot_row_number=1,
    plot_column_number=1,
    plot_info={"test": "test"},
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1",
    population_accession="Accession A1",
    population_name="Population A"
)
print(f"Created New Plot: {new_plot}")

# Associate the plant with the plot
new_plant.associate_plot(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Associated Plant with Plot: {new_plant}")

# Check if the plant is associated with the plot
is_associated_plot = new_plant.belongs_to_plot(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Is Plant associated with Plot: {is_associated_plot}")

# Unassociate the plant from the plot
new_plant.unassociate_plot()
print(f"Unassociated Plant from Plot: {new_plant}")

# Check if the plant is unassociated from the plot
is_unassociated_plot = new_plant.belongs_to_plot(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Is Plant unassociated from Plot: {is_unassociated_plot}")
```

## Explanation

This example demonstrates how to manage the association between plots and plants:

*   **Creating a plant:** The `Plant.create()` method is used to create a new plant with a plant number and additional information.
*   **Creating a plot:** The `Plot.create()` method is used to create a new plot with plot information, additional information, and associated experiment, season, site, and population.
*   **Associating with a plot:** The `associate_plot()` method associates the plant with the created plot.
*   **Checking association:** The `belongs_to_plot()` method verifies if the plant is associated with a specific plot.
*   **Unassociating from a plot:** The `unassociate_plot()` method removes the association between the plant and the plot.
*   **Verifying unassociation:** The `belongs_to_plot()` method is used again to confirm that the plant is no longer associated with the plot.
