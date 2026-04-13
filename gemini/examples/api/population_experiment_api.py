from gemini.api.population import Population

new_population = Population.create(
    population_name="Population Test 1",
    population_type="diversity_panel",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created Population: {new_population}")

associated_experiments = new_population.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

new_population.associate_experiment(experiment_name="Experiment B")
print(f"Associated Population with Experiment B")

is_associated = new_population.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Population associated with Experiment B? {is_associated}")

new_population.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Population from Experiment B")

is_associated_after = new_population.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Population still associated with Experiment B? {is_associated_after}")
