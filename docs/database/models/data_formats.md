# Data Formats

The `data_formats` table stores information about the different data formats supported by the GEMINIbase.

## Table Schema

| Column Name             | Data Type      | Description                                                                                      |
| ----------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `id`                    | `Integer`      | **Primary Key.** A unique identifier for the data format.                                        |
| `data_format_name`      | `String(255)`  | The name of the data format (e.g., "CSV", "JSON"). This column has a unique constraint.          |
| `data_format_mime_type` | `String(255)`  | The MIME type associated with the data format. Defaults to 'application/octet-stream'.           |
| `data_format_info`      | `JSONB`        | A JSONB column for storing additional, unstructured information about the data format.           |
| `created_at`            | `TIMESTAMP`    | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`            | `TIMESTAMP`    | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `data_format_name` ensures that each data format has a unique name.
- **GIN Index:** A GIN index named `idx_data_formats_info` is applied to the `data_format_info` column to optimize queries on the JSONB data.

## Relationships

The `data_formats` table is referenced by other tables that need to specify a data format, such as `data_types`.
