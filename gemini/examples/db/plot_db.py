from gemini.db.models.plots import PlotModel

plots = PlotModel.all()

print("Plots:")
for plot in plots:
    print(f"{plot.id}: {plot.plot_number}")
    print(f"Experiment: {plot.experiment_id}")
    print(f"Accession: {plot.accession_id}")
    print(f"Population: {plot.population_id}")
    print(f"Site: {plot.site_id}")
    print(f"Season: {plot.season_id}")
