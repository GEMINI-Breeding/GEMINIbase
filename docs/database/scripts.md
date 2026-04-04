# Database Initialization Scripts

This section provides an overview of the SQL scripts used to initialize the GEMINI database. These scripts are located in the `gemini/db/init_sql/scripts/` directory.

## Script Locations

- **1_init_db.sh**: `gemini/db/init_sql/1_init_db.sh`
- **2_init_schema.sql**: `gemini/db/init_sql/scripts/2_init_schema.sql`
- **4_init_columnar.sql**: `gemini/db/init_sql/scripts/4_init_columnar.sql`
- **5_init_views.sql**: `gemini/db/init_sql/scripts/5_init_views.sql`
- **6_init_functions.sql**: `gemini/db/init_sql/scripts/6_init_functions.sql`

## 1_init_db.sh

This shell script is the entry point for initializing the database. It performs the following steps:

- Checks if the database already exists.
- Creates the database if it doesn't exist.
- Applies the SQL scripts to create the schema and initial data.

## 2_init_schema.sql

This SQL script defines the database schema, including:

- Creation of tables for main entities such as `populations`, `data_formats`, `data_types`, `datasets`, `experiments`, `models`, `plants`, `plots`, `procedures`, `resources`, `scripts`, `seasons`, `sensor_platforms`, `sensor_types`, `sensors`, `sites`, `trait_levels`, and `traits`.
- Definition of data types for each column in the tables.
- Definition of primary keys and foreign keys to establish relationships between tables.
- Creation of unique constraints and indexes to ensure data integrity and optimize query performance.

## 4_init_columnar.sql

This SQL script creates the columnar tables for storing time series data.

- Creation of tables for `dataset_records`, `model_records`, `procedure_records`, `script_records`, `sensor_records`, and `trait_records`.
- Definition of data types for each column in the tables, optimized for columnar storage.
- Creation of unique constraints and indexes to ensure data integrity and optimize query performance.

## 5_init_views.sql

This SQL script creates the views for simplifying data access.

- Creation of views for `experiment_datasets_view`, `experiment_models_view`, `experiment_procedures_view`, `experiment_scripts_view`, `experiment_seasons_view`, `experiment_sensors_view`, `experiment_sites_view`, `experiment_traits_view`, `model_runs_view`, `plant_view`, `plot_population_view`, `procedure_runs_view`, `script_runs_view`, `sensor_platform_sensors_view`, `sensor_datasets_view`, `trait_datasets_view`, `datatype_format_view`, `ValidPlotCombinationsView`, `ValidDatasetCombinationsView`, `ValidSensorDatasetCombinationsView`, `ValidTraitDatasetCombinationsView`, `ValidProcedureDatasetCombinationsView`, `ValidModelDatasetCombinationsView`, `ValidScriptDatasetCombinationsView`.

## 6_init_functions.sql

This SQL script creates the functions for filtering data.

- Creation of functions for `filter_dataset_records`, `filter_model_records`, `filter_procedure_records`, `filter_script_records`, `filter_sensor_records`, and `filter_trait_records`.
