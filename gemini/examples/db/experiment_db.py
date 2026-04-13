from gemini.db.models.experiments import ExperimentModel

experiments = ExperimentModel.all()

for experiment in experiments:
    print(f"Experiment: {experiment.experiment_name}")
