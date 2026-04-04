# Experiment Populations

The `experiment_populations` table links experiments with the populations being studied.

## Table Schema

| Column Name     | Data Type | Description                                             |
| --------------- | --------- | ------------------------------------------------------- |
| `experiment_id` | `UUID`    | **Primary Key, Foreign Key.** Links to `experiments.id`. |
| `population_id`   | `UUID`    | **Primary Key, Foreign Key.** Links to `populations.id`.   |
