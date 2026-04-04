# Experiment Views

This section describes the views related to experiments, which provide simplified or aggregated access to experiment-related information.

## Experiment Seasons View (`experiment_seasons_view`)

This view combines information from experiments and seasons.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `season_id`           | `UUID`         | Unique identifier for the season.                                                                |
| `season_name`         | `String`       | The name of the season.                                                                          |
| `season_start_date`     | `String`       | The start date of the season.                                                                    |
| `season_end_date`       | `String`       | The end date of the season.                                                                      |
| `season_info`         | `JSONB`         | Additional JSONB data for the season.                                                                |

## Experiment Sites View (`experiment_sites_view`)

This view combines information from experiments and sites.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `site_id`             | `UUID`         | Unique identifier for the site.                                                                  |
| `site_name`           | `String`       | The name of the site.                                                                            |
| `site_city`           | `String`       | The city where the site is located.                                                              |
| `site_state`          | `String`       | The state where the site is located.                                                             |
| `site_country`        | `String`       | The country where the site is located.                                                           |
| `site_info`           | `JSONB`         | Additional JSONB data for the site.                                                                |

## Experiment Traits View (`experiment_traits_view`)

This view combines information from experiments and traits.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `trait_id`            | `UUID`         | Unique identifier for the trait.                                                                 |
| `trait_name`          | `String`       | The name of the trait.                                                                           |
| `trait_units`         | `String`       | The units in which the trait is measured.                                                        |
| `trait_metrics`       | `String`         | The metrics of the trait.                                                                        |
| `trait_level_id`      | `Integer`      | Foreign key referencing the trait level.                                                         |
| `trait_info`          | `JSONB`         | Additional JSONB data for the trait.                                                                 |

## Experiment Sensors View (`experiment_sensors_view`)

This view combines information from experiments and sensors.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `sensor_id`           | `UUID`         | Unique identifier for the sensor.                                                                |
| `sensor_name`           | `String`       | The name of the sensor.                                                                          |
| `sensor_type_id`      | `Integer`      | Foreign key referencing the sensor type.                                                         |
| `sensor_data_type_id` | `Integer`      | Foreign key referencing the data type of the sensor's data.                                      |
| `sensor_data_format_id`| `Integer`      | Foreign key referencing the data format of the sensor's data.                                  |
| `sensor_info`           | `JSONB`         | Additional JSONB data for the sensor.                                                                |

## Experiment Sensor Platforms View (`experiment_sensor_platforms_view`)

This view combines information from experiments and sensor platforms.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `sensor_platform_id`  | `UUID`         | Unique identifier for the sensor platform.                                                       |
| `sensor_platform_name`| `String`       | The name of the sensor platform.                                                                 |
| `sensor_platform_info`| `JSONB`         | Additional JSONB data for the sensor platform.                                                       |

## Experiment Populations View (`experiment_populations_view`)

This view combines information from experiments and populations.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `population_id`         | `UUID`         | Unique identifier for the population.                                                              |
| `population_accession`  | `String`       | The accession identifier for the population.                                                       |
| `population_name` | `String`       | The population name of the population.                                                             |
| `population_info`       | `JSONB`         | Additional JSONB data for the population.                                                              |

## Experiment Procedures View (`experiment_procedures_view`)

This view combines information from experiments and procedures.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `procedure_id`        | `UUID`         | Unique identifier for the procedure.                                                             |
| `procedure_name`      | `String`       | The name of the procedure.                                                                       |
| `procedure_info`       | `JSONB`         | Additional JSONB data for the procedure.                                                               |

## Experiment Scripts View (`experiment_scripts_view`)

This view combines information from experiments and scripts.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `script_id`           | `UUID`         | Unique identifier for the script.                                                                |
| `script_name`         | `String`       | The name of the script.                                                                          |
| `script_url`          | `String`       | The URL where the script can be accessed.                                                        |
| `script_extension`    | `String`       | The file extension of the script.                                                                |
| `script_info`           | `JSONB`         | Additional JSONB data for the script.                                                                |

## Experiment Models View (`experiment_models_view`)

This view combines information from experiments and models.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `model_id`            | `UUID`         | Unique identifier for the model.                                                                 |
| `model_name`          | `String`       | The name of the model.                                                                           |
| `model_url`           | `String`       | The URL where the model can be accessed.                                                         |
| `model_info`           | `JSONB`         | Additional JSONB data for the model.                                                                 |

## Experiment Datasets View (`experiment_datasets_view`)

This view combines information from experiments and datasets.

### View Schema

| Column Name           | Data Type      | Description                                                                                      |
| --------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `experiment_id`       | `UUID`         | Unique identifier for the experiment.                                                            |
| `experiment_name`     | `String`       | The name of the experiment.                                                                      |
| `experiment_info`       | `JSONB`         | Additional JSONB data for the experiment.                                                            |
| `experiment_start_date` | `String`       | The start date of the experiment.                                                                |
| `experiment_end_date`   | `String`       | The end date of the experiment.                                                                  |
| `dataset_id`          | `UUID`         | Unique identifier for the dataset.                                                               |
| `collection_date`     | `String`       | The date when the data was collected.                                                            |
| `dataset_name`        | `String`       | The name of the dataset.                                                                         |
| `dataset_type_id`      | `Integer`      | Foreign key referencing the dataset type.                                                        |
| `dataset_info`          | `JSONB`         | Additional JSONB data for the dataset.                                                                 |
