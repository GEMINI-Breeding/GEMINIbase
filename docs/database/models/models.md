# Models

The `models` table stores information about the predictive or analytical models used in the GEMINIbase.

## Table Schema

| Column Name  | Data Type      | Description                                                                                      |
| ------------ | -------------- | ------------------------------------------------------------------------------------------------ |
| `id`         | `UUID`         | **Primary Key.** A unique identifier for the model.                                              |
| `model_name` | `String(255)`  | The name of the model.                                                                           |
| `model_url`  | `String(255)`  | The URL where the model can be accessed.                                                         |
| `model_info` | `JSONB`        | A JSONB column for storing additional, unstructured information about the model.                 |
| `created_at` | `TIMESTAMP`    | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at` | `TIMESTAMP`    | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `model_name` and `model_url` ensures that each combination is unique.
- **GIN Index:** A GIN index named `idx_models_info` is applied to the `model_info` column to optimize queries on the JSONB data.

## Relationships

- **`model_runs`:** A one-to-many relationship with the `model_runs` table, where one model can have multiple runs.
- **Association Tables:** The `models` table is linked to other entities like `experiments` and `datasets` through association tables.
