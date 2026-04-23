# Datasets

The `datasets` table is a central table in the GEMINIbase database, storing metadata about each dataset.

## Table Schema

| Column Name       | Data Type   | Description                                                                                      |
| ----------------- | ----------- | ------------------------------------------------------------------------------------------------ |
| `id`              | `UUID`      | **Primary Key.** A unique identifier for the dataset.                                            |
| `collection_date` | `TIMESTAMP` | The date when the dataset was collected.                                                         |
| `dataset_name`    | `String(255)` | The name of the dataset. This column has a unique constraint.                                    |
| `dataset_info`    | `JSONB`     | A JSONB column for storing additional, unstructured information about the dataset.               |
| `dataset_type_id` | `Integer`   | **Foreign Key.** References the `id` of the dataset type in the `dataset_types` table.           |
| `created_at`      | `TIMESTAMP` | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`      | `TIMESTAMP` | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `dataset_name` ensures that each dataset has a unique name.
- **GIN Index:** A GIN index named `idx_datasets_info` is applied to the `dataset_info` column to optimize queries on the JSONB data.

## Relationships

- **`dataset_type`:** A many-to-one relationship with the `dataset_types` table, linking each dataset to its corresponding type.
- **Association Tables:** The `datasets` table is linked to many other tables through various association tables, such as `experiment_datasets`, `sensor_datasets`, etc., to create a comprehensive data network.
