# Plants

The `plants` table stores information about individual plants within a plot.

## Table Schema

| Column Name    | Data Type   | Description                                                                                      |
| -------------- | ----------- | ------------------------------------------------------------------------------------------------ |
| `id`           | `UUID`      | **Primary Key.** A unique identifier for the plant.                                              |
| `plot_id`      | `UUID`      | **Foreign Key.** References the `id` of the plot where the plant is located.                     |
| `plant_number` | `Integer`   | The number of the plant within the plot.                                                         |
| `plant_info`   | `JSONB`     | A JSONB column for storing additional, unstructured information about the plant.                 |
| `population_id`  | `UUID`      | **Foreign Key.** References the `id` of the population for this plant.                             |
| `created_at`   | `TIMESTAMP` | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`   | `TIMESTAMP` | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `plot_id` and `plant_number` ensures that each plant number is unique within a plot.
- **GIN Index:** A GIN index named `idx_plants_info` is applied to the `plant_info` column to optimize queries on the JSONB data.

## Relationships

- **`plot`:** A many-to-one relationship with the `plots` table.
- **`population`:** A many-to-one relationship with the `populations` table.
