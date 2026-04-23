# Data Types

The `data_types` table stores information about the different types of data that can be collected and analyzed within the GEMINIbase.

## Table Schema

| Column Name      | Data Type      | Description                                                                                      |
| ---------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `id`             | `Integer`      | **Primary Key.** A unique identifier for the data type.                                          |
| `data_type_name` | `String(255)`  | The name of the data type (e.g., "Temperature", "Humidity"). This column has a unique constraint. |
| `data_type_info` | `JSONB`        | A JSONB column for storing additional, unstructured information about the data type.             |
| `created_at`     | `TIMESTAMP`    | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`     | `TIMESTAMP`    | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `data_type_name` ensures that each data type has a unique name.
- **GIN Index:** A GIN index named `idx_data_types_info` is applied to the `data_type_info` column to optimize queries on the JSONB data.

## Relationships

The `data_types` table is associated with the `data_formats` table through the `data_type_formats` association table, indicating which formats are available for each data type.
