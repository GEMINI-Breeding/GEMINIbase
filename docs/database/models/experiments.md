# Experiments

The `experiments` table stores information about the experiments conducted.

## Table Schema

| Column Name             | Data Type   | Description                                                                                      |
| ----------------------- | ----------- | ------------------------------------------------------------------------------------------------ |
| `id`                    | `UUID`      | **Primary Key.** A unique identifier for the experiment.                                         |
| `experiment_name`       | `String(255)` | The name of the experiment. This column has a unique constraint.                                 |
| `experiment_info`       | `JSONB`     | A JSONB column for storing additional, unstructured information about the experiment.            |
| `experiment_start_date` | `DATE`      | The start date of the experiment.                                                                |
| `experiment_end_date`   | `DATE`      | The end date of the experiment.                                                                  |
| `created_at`            | `TIMESTAMP` | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`            | `TIMESTAMP` | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `experiment_name` ensures that each experiment has a unique name.
- **Check Constraint:** Ensures that `experiment_start_date` is less than or equal to `experiment_end_date`.
- **GIN Index:** A GIN index named `idx_experiments_info` is applied to the `experiment_info` column to optimize queries on the JSONB data.

## Relationships

The `experiments` table is a central entity and is linked to many other tables through association tables, such as `experiment_sites`, `experiment_sensors`, `experiment_populations`, etc., to define the scope and components of each experiment.
