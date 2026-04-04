# Plot Populations

The `plot_populations` table links plots to the populations planted in them.

## Table Schema

| Column Name   | Data Type | Description                                           |
| ------------- | --------- | ----------------------------------------------------- |
| `plot_id`     | `UUID`    | **Primary Key, Foreign Key.** Links to `plots.id`.     |
| `population_id` | `UUID`    | **Primary Key, Foreign Key.** Links to `populations.id`. |
