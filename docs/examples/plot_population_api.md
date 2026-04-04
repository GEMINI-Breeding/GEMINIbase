# Plot Population API Example

This example demonstrates how to associate and unassociate populations with plots using the Gemini framework.

## Source File Location

The original Python script is located at `gemini/examples/api/plot_population_api.py`.

## Code

```python
from gemini.api.plot import Plot
from gemini.api.population import Population

try:
    # Create a new Plot for Experiment A
    new_plot = Plot.create(
        plot_number=2000,
        plot_row_number=101,
        plot_column_number=101,
        experiment_name="Experiment A",
        season_name="Season 1A",
        site_name="Site A1",
        plot_info={"test": "test"},
    )
    print(f"Created Plot: {new_plot}")

    # Create a new Population for Experiment A
    new_population = Population.create(
        population_name="Population Test 1",
        population_accession="Accession A",
        population_info={"test": "test"},
        experiment_name="Experiment A"
    )
    print(f"Created Population: {new_population}")

    # Associate the plot with the population
    new_plot.associate_population(
        population_name="Population Test 1",
        population_accession="Accession A"
    )
    print(f"Associated Plot with Population: {new_plot}")

    # Check if the plot is associated with the population
    is_associated_population = new_plot.belongs_to_population(
        population_name="Population Test 1",
        population_accession="Accession A"
    )
    print(f"Is Plot associated with Population: {is_associated_population}")

    # Unassociate the plot from the population
    new_plot.unassociate_population(
        population_name="Population Test 1",
        population_accession="Accession A"
    )
    print(f"Unassociated Plot from Population: {new_plot}")

    # Check if the plot is unassociated from the population
    is_unassociated_population = new_plot.belongs_to_population(
        population_name="Population Test 1",
        population_accession="Accession A"
    )
    print(f"Is Plot unassociated from Population: {is_unassociated_population}")
    

finally:
    # Clean up: Delete the created plot and population
    if new_plot:
        new_plot.delete()
        print(f"Deleted Plot: {new_plot}")

    if new_population:
        new_population.delete()
        print(f"Deleted Population: {new_population}")
```

## Explanation

This example demonstrates how to manage the association between populations and plots:

*   **Creating a plot:** The `Plot.create()` method is used to create a new plot with plot information, additional information, and associated experiment, season, and site.
*   **Creating a population:** The `Population.create()` method is used to create a new population with a population, accession, additional information, and associated experiment.
*   **Associating with a population:** The `associate_population()` method associates the plot with the created population.
*   **Checking association:** The `belongs_to_population()` method verifies if the plot is associated with a specific population.
*   **Unassociating from a population:** The `unassociate_population()` method removes the association between the plot and the population.
*   **Verifying unassociation:** The `belongs_to_population()` method is used again to confirm that the plot is no longer associated with the population.
*   **Cleaning up:** The `delete()` method is used to delete the created plot and population.
