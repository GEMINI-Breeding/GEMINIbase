# Plots

The `plots` table defines the spatial layout of an experiment, breaking it down into individual plots.

## Table Schema

| Column Name          | Data Type   | Description                                                                                      |
| -------------------- | ----------- | ------------------------------------------------------------------------------------------------ |
| `id`                 | `UUID`      | **Primary Key.** A unique identifier for the plot.                                               |
| `experiment_id`      | `UUID`      | **Foreign Key.** References the `id` of the experiment to which the plot belongs.                |
| `season_id`          | `UUID`      | **Foreign Key.** References the `id` of the season during which the plot was used.               |
| `site_id`            | `UUID`      | **Foreign Key.** References the `id` of the site where the plot is located.                      |
| `plot_number`        | `Integer`   | The number of the plot.                                                                          |
| `plot_row_number`    | `Integer`   | The row number of the plot in a grid layout.                                                     |
| `plot_column_number` | `Integer`   | The column number of the plot in a grid layout.                                                  |
| `plot_geometry_info` | `JSONB`     | A JSONB column for storing additional, unstructured information about the plot's geometry.       |
| `plot_info`          | `JSONB`     | A JSONB column for storing additional, unstructured information about the plot.                  |
| `accession_id`       | `UUID`      | **Foreign Key.** References the `id` of the accession planted in this plot.                      |
| `population_id`      | `UUID`      | **Foreign Key.** References the `id` of the population planted in this plot.                     |
| `created_at`         | `TIMESTAMP` | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`         | `TIMESTAMP` | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `experiment_id`, `season_id`, `site_id`, `plot_number`, `plot_row_number`, and `plot_column_number` ensures that each plot is uniquely defined within an experiment for a given season and site.
- **GIN Index:** A GIN index named `idx_plots_info` is applied to the `plot_info` column to optimize queries on the JSONB data.

## Relationships

- **`experiment`:** A many-to-one relationship with the `experiments` table.
- **`season`:** A many-to-one relationship with the `seasons` table.
- **`site`:** A many-to-one relationship with the `sites` table.
- **`accession`:** A many-to-one relationship with the `accessions` table via `accession_id`.
- **`population`:** A many-to-one relationship with the `populations` table via `population_id`.
