from gemini.api.plot import Plot

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

plot_by_id = Plot.get_by_id(new_plot.id)
print(f"Got Plot by ID: {plot_by_id}")

plot = Plot.get(
    plot_number=new_plot.plot_number,
    plot_row_number=new_plot.plot_row_number,
    plot_column_number=new_plot.plot_column_number,
    experiment_name="Experiment A",
    season_name="Season 1A",
    site_name="Site A1"
)
print(f"Got Plot: {plot}")

all_plots = Plot.get_all()
print(f"All Plots:")
for p in all_plots[:10]:
    print(p)

searched_plots = Plot.search(experiment_name="Experiment A")
length_searched_plots = len(searched_plots)
print(f"Found {length_searched_plots} plots in Experiment A")

plot.refresh()
print(f"Refreshed Plot: {plot}")

accession = plot.get_accession()
print(f"Plot accession: {accession}")

population = plot.get_population()
print(f"Plot population: {population}")

is_deleted = new_plot.delete()
print(f"Deleted Plot: {is_deleted}")
