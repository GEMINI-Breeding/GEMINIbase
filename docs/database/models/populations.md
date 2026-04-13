# Populations

The `populations` table stores information about different plant populations used in experiments. Each row represents a unique population, identified by its name.

## Table Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `id`                  | `UUID`         | **Primary Key.** A unique identifier for the population.                                           |
| `population_name`     | `String(255)`  | The name of the population. Must be unique.                                                        |
| `population_type`     | `String(255)`  | The type of the population (e.g., breeding, natural).                                              |
| `species`             | `String(255)`  | The species of the population.                                                                     |
| `population_info`     | `JSONB`        | A JSONB column for storing additional, unstructured information about the population.              |
| `created_at`          | `TIMESTAMP`    | The timestamp when the record was created. Defaults to the current time.                         |
| `updated_at`          | `TIMESTAMP`    | The timestamp when the record was last updated. Automatically updates on any modification.       |

## Constraints and Indexes

- **Unique Constraint:** A `UniqueConstraint` on `population_name` ensures that each population name is unique within the table.
- **GIN Index:** A GIN index named `idx_populations_info` is applied to the `population_info` column to optimize queries on the JSONB data.

## Relationships

The `populations` table is related to other tables in the database, such as `experiments` and `plots`, to associate experimental data with specific populations. These relationships are defined in the corresponding association tables.
