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