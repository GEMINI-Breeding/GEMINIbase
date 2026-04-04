from gemini.api.population import Population

# Create a new population for Experiment A
new_population = Population.create(
    population_name="Population Test 1",
    population_accession="Accession A",
    population_info={"test": "test"},
    experiment_name="Experiment A"
)
print(f"Created Population: {new_population}")

# Get Associated Experiments
associated_experiments = new_population.get_associated_experiments()
for experiment in associated_experiments:
    print(f"Associated Experiment: {experiment}")

# Associate the population with Experiment B
new_population.associate_experiment(experiment_name="Experiment B")
print(f"Associated Population with Experiment B")

# Check if the population is associated with Experiment B
is_associated = new_population.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Population associated with Experiment B? {is_associated}")

# Unassociate the population from Experiment B
new_population.unassociate_experiment(experiment_name="Experiment B")
print(f"Unassociated Population from Experiment B")

# Verify the unassociation
is_associated_after_unassociation = new_population.belongs_to_experiment(experiment_name="Experiment B")
print(f"Is Population still associated with Experiment B? {is_associated_after_unassociation}")