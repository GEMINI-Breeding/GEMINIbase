# Dataset Types

The `dataset_types` table categorizes the datasets stored in the GEMINIbase. This helps in organizing and querying datasets based on their nature.

## Table Schema

| Column Name         | Data Type      | Description                                                                                      |
| ------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `id`                | `Integer`      | **Primary Key.** A unique identifier for the dataset type.                                       |
| `dataset_type_name` | `String(255)`  | The name of the dataset type (e.g., "Phenotypic", "Genotypic"). This column has a unique constraint. |
| `dataset_type_info` | `JSONB`        | A JSONB column for storing additional, unstructured information about the dataset type.          |
| `created_at`        | `TIMESTAMP`    | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`        | `TIMESTAMP`    | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `dataset_type_name` ensures that each dataset type has a unique name.
- **GIN Index:** A GIN index named `idx_dataset_types_info` is applied to the `dataset_type_info` column to optimize queries on the JSONB data.

## Relationships

The `dataset_types` table is referenced by the `datasets` table to categorize each dataset.
