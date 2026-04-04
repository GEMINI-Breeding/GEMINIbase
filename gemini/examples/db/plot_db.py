from gemini.db.models.plots import PlotModel

# Get All Plots
plots = PlotModel.all()

# Print Plots
print("Plots:")
for plot in plots:
    print(f"{plot.id}: {plot.plot_number}")

    # Print Populations of Plot
    for population in plot.populations:
        print(f"Population: {population.population_accession} {population.population_name}")


    # Print Plants of Plot
    for plant in plot.plants:
        print(f"Plant: {plant.plant_number}")

    # Print Experiment of Plot
    print(f"Experiment: {plot.experiment.experiment_name}")
    # Print Site of Plot
    print(f"Site: {plot.site.site_name}")
    # Print Season of Plot
    print(f"Season: {plot.season.season_name}")
