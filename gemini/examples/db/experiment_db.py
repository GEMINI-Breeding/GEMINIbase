from gemini.db.models.experiments import ExperimentModel

# Get all experiments
experiments = ExperimentModel.all()

# Get all experiment resources
for experiment in experiments:
    print(f"Experiment: {experiment.experiment_name}")
    for resource in experiment.resources:
        print(f"Resource: {resource.id}")
    for season in experiment.seasons:
        print(f"Season: {season.season_name}")
    for site in experiment.sites:
        print(f"Site: {site.site_name}")
    for sensor in experiment.sensors:
        print(f"Sensor: {sensor.sensor_name}")
    for population in experiment.populations:
        print(f"Population: {population.population_accession} {population.population_name}")
    for dataset in experiment.datasets:
        print(f"Dataset: {dataset.dataset_name}")
    for trait in experiment.traits:
        print(f"Trait: {trait.trait_name}")
    for model in experiment.models:
        print(f"Model: {model.model_name}")
    for script in experiment.scripts:
        print(f"Script: {script.script_name}")
    for procedure in experiment.procedures:
        print(f"Procedure: {procedure.procedure_name}")
    for platform in experiment.platforms:
        print(f"Platform: {platform.sensor_platform_name}")
