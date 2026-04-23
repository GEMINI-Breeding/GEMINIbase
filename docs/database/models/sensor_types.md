# Sensor Types

The `sensor_types` table categorizes the sensors used in the GEMINIbase.

## Table Schema

| Column Name      | Data Type      | Description                                                                                      |
| ---------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `id`             | `Integer`      | **Primary Key.** A unique identifier for the sensor type.                                        |
| `sensor_type_name` | `String(255)`  | The name of the sensor type (e.g., "Temperature", "Humidity"). This column has a unique constraint. |
| `sensor_type_info` | `JSONB`        | A JSONB column for storing additional, unstructured information about the sensor type.           |
| `created_at`     | `TIMESTAMP`    | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`     | `TIMESTAMP`    | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `sensor_type_name` ensures that each sensor type has a unique name.
- **GIN Index:** A GIN index named `idx_sensor_types_info` is applied to the `sensor_type_info` column to optimize queries on the JSONB data.

## Relationships

- **`sensors`:** A one-to-many relationship with the `sensors` table, where one sensor type can be associated with multiple sensors.
