# Experiments API

The Experiments API provides endpoints for managing and retrieving experiment data and their associated entities.

## Get All Experiments

- **Endpoint:** `/all`
- **Method:** `GET`
- **Description:** Retrieves a list of all experiments in the database.
- **Responses:**
  - `200 OK`: A list of experiment objects.
  - `404 Not Found`: If no experiments are found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Search for Experiments

- **Endpoint:** `/`
- **Method:** `GET`
- **Description:** Searches for experiments based on the provided criteria.
- **Query Parameters:**
  - `experiment_name` (optional): The name of the experiment.
  - `experiment_info` (optional): Additional information about the experiment in JSON format.
  - `experiment_start_date` (optional): The start date of the experiment.
  - `experiment_end_date` (optional): The end date of the experiment.
- **Responses:**
  - `200 OK`: A list of matching experiment objects.
  - `404 Not Found`: If no experiments match the search criteria.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Experiment by ID

- **Endpoint:** `/id/{experiment_id}`
- **Method:** `GET`
- **Description:** Retrieves a specific experiment by its unique ID.
- **Path Parameter:**
  - `experiment_id`: The ID of the experiment to retrieve.
- **Responses:**
  - `200 OK`: The requested experiment object.
  - `404 Not Found`: If the experiment with the given ID is not found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create a New Experiment

- **Endpoint:** `/`
- **Method:** `POST`
- **Description:** Creates a new experiment in the database.
- **Request Body:**
  - `experiment_name`: The name of the experiment.
  - `experiment_info`: Additional information about the experiment.
  - `experiment_start_date`: The start date of the experiment.
  - `experiment_end_date`: The end date of the experiment.
- **Responses:**
  - `200 OK`: The newly created experiment object.
  - `500 Internal Server Error`: If the experiment cannot be created.

## Update an Existing Experiment

- **Endpoint:** `/id/{experiment_id}`
- **Method:** `PATCH`
- **Description:** Updates an existing experiment's information.
- **Path Parameter:**
  - `experiment_id`: The ID of the experiment to update.
- **Request Body:**
  - `experiment_name` (optional): The new name of the experiment.
  - `experiment_info` (optional): New information about the experiment.
  - `experiment_start_date` (optional): The new start date of the experiment.
  - `experiment_end_date` (optional): The new end date of the experiment.
- **Responses:**
  - `200 OK`: The updated experiment object.
  - `404 Not Found`: If the experiment with the given ID is not found.
  - `500 Internal Server Error`: If the experiment cannot be updated.

## Delete an Experiment

- **Endpoint:** `/id/{experiment_id}`
- **Method:** `DELETE`
- **Description:** Deletes an experiment from the database.
- **Path Parameter:**
  - `experiment_id`: The ID of the experiment to delete.
- **Responses:**
  - `200 OK`: If the experiment is successfully deleted.
  - `404 Not Found`: If the experiment with the given ID is not found.
  - `500 Internal Server Error`: If the experiment cannot be deleted.

## Get Experiment Seasons

- **Endpoint:** `/id/{experiment_id}/seasons`
- **Method:** `GET`
- **Description:** Retrieves all seasons associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated season objects.
  - `404 Not Found`: If the experiment is not found or has no associated seasons.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Season for Experiment

- **Endpoint:** `/id/{experiment_id}/seasons`
- **Method:** `POST`
- **Description:** Creates a new season for a specific experiment.
- **Request Body:**
  - `season_name`: The name of the season.
  - `season_info`: Additional information about the season.
  - `season_start_date`: The start date of the season.
  - `season_end_date`: The end date of the season.
- **Responses:**
  - `200 OK`: The newly created season object.
  - `500 Internal Server Error`: If the season cannot be created.

## Get Experiment Sites

- **Endpoint:** `/id/{experiment_id}/sites`
- **Method:** `GET`
- **Description:** Retrieves all sites associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated site objects.
  - `404 Not Found`: If the experiment is not found or has no associated sites.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Site for Experiment

- **Endpoint:** `/id/{experiment_id}/sites`
- **Method:** `POST`
- **Description:** Creates a new site for a specific experiment.
- **Request Body:**
  - `site_name`: The name of the site.
  - `site_info`: Additional information about the site.
  - `site_city`: The city where the site is located.
  - `site_state`: The state where the site is located.
  - `site_country`: The country where the site is located.
- **Responses:**
  - `200 OK`: The newly created site object.
  - `500 Internal Server Error`: If the site cannot be created.

## Get Experiment Populations

- **Endpoint:** `/id/{experiment_id}/populations`
- **Method:** `GET`
- **Description:** Retrieves all populations associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated population objects.
  - `404 Not Found`: If the experiment is not found or has no associated populations.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Population for Experiment

- **Endpoint:** `/id/{experiment_id}/populations`
- **Method:** `POST`
- **Description:** Creates a new population for a specific experiment.
- **Request Body:**
  - `population_name`: The population of the population.
  - `population_accession`: The accession number of the population.
  - `population_info`: Additional information about the population.
- **Responses:**
  - `200 OK`: The newly created population object.
  - `500 Internal Server Error`: If the population cannot be created.

## Get Experiment Sensor Platforms

- **Endpoint:** `/id/{experiment_id}/sensor_platforms`
- **Method:** `GET`
- **Description:** Retrieves all sensor platforms associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated sensor platform objects.
  - `404 Not Found`: If the experiment is not found or has no associated sensor platforms.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Sensor Platform for Experiment

- **Endpoint:** `/id/{experiment_id}/sensor_platforms`
- **Method:** `POST`
- **Description:** Creates a new sensor platform for a specific experiment.
- **Request Body:**
  - `sensor_platform_name`: The name of the sensor platform.
  - `sensor_platform_info`: Additional information about the sensor platform.
- **Responses:**
  - `200 OK`: The newly created sensor platform object.
  - `500 Internal Server Error`: If the sensor platform cannot be created.

## Get Experiment Traits

- **Endpoint:** `/id/{experiment_id}/traits`
- **Method:** `GET`
- **Description:** Retrieves all traits associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated trait objects.
  - `404 Not Found`: If the experiment is not found or has no associated traits.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Trait for Experiment

- **Endpoint:** `/id/{experiment_id}/traits`
- **Method:** `POST`
- **Description:** Creates a new trait for a specific experiment.
- **Request Body:**
  - `trait_name`: The name of the trait.
  - `trait_units`: The units of the trait.
  - `trait_level_id`: The ID of the trait level.
  - `trait_info`: Additional information about the trait.
  - `trait_metrics`: Metrics associated with the trait.
- **Responses:**
  - `200 OK`: The newly created trait object.
  - `500 Internal Server Error`: If the trait cannot be created.

## Get Experiment Sensors

- **Endpoint:** `/id/{experiment_id}/sensors`
- **Method:** `GET`
- **Description:** Retrieves all sensors associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated sensor objects.
  - `404 Not Found`: If the experiment is not found or has no associated sensors.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Sensor for Experiment

- **Endpoint:** `/id/{experiment_id}/sensors`
- **Method:** `POST`
- **Description:** Creates a new sensor for a specific experiment.
- **Request Body:**
  - `sensor_name`: The name of the sensor.
  - `sensor_data_type_id`: The ID of the sensor data type.
  - `sensor_data_format_id`: The ID of the sensor data format.
  - `sensor_type_id`: The ID of the sensor type.
  - `sensor_info`: Additional information about the sensor.
  - `sensor_platform_name`: The name of the associated sensor platform.
- **Responses:**
  - `200 OK`: The newly created sensor object.
  - `500 Internal Server Error`: If the sensor cannot be created.

## Get Experiment Scripts

- **Endpoint:** `/id/{experiment_id}/scripts`
- **Method:** `GET`
- **Description:** Retrieves all scripts associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated script objects.
  - `404 Not Found`: If the experiment is not found or has no associated scripts.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Script for Experiment

- **Endpoint:** `/id/{experiment_id}/scripts`
- **Method:** `POST`
- **Description:** Creates a new script for a specific experiment.
- **Request Body:**
  - `script_name`: The name of the script.
  - `script_extension`: The extension of the script file.
  - `script_url`: The URL of the script.
  - `script_info`: Additional information about the script.
- **Responses:**
  - `200 OK`: The newly created script object.
  - `500 Internal Server Error`: If the script cannot be created.

## Get Experiment Procedures

- **Endpoint:** `/id/{experiment_id}/procedures`
- **Method:** `GET`
- **Description:** Retrieves all procedures associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated procedure objects.
  - `404 Not Found`: If the experiment is not found or has no associated procedures.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Procedure for Experiment

- **Endpoint:** `/id/{experiment_id}/procedures`
- **Method:** `POST`
- **Description:** Creates a new procedure for a specific experiment.
- **Request Body:**
  - `procedure_name`: The name of the procedure.
  - `procedure_info`: Additional information about the procedure.
- **Responses:**
  - `200 OK`: The newly created procedure object.
  - `500 Internal Server Error`: If the procedure cannot be created.

## Get Experiment Models

- **Endpoint:** `/id/{experiment_id}/models`
- **Method:** `GET`
- **Description:** Retrieves all models associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated model objects.
  - `404 Not Found`: If the experiment is not found or has no associated models.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Model for Experiment

- **Endpoint:** `/id/{experiment_id}/models`
- **Method:** `POST`
- **Description:** Creates a new model for a specific experiment.
- **Request Body:**
  - `model_name`: The name of the model.
  - `model_url`: The URL of the model.
  - `model_info`: Additional information about the model.
- **Responses:**
  - `200 OK`: The newly created model object.
  - `500 Internal Server Error`: If the model cannot be created.

## Get Experiment Datasets

- **Endpoint:** `/id/{experiment_id}/datasets`
- **Method:** `GET`
- **Description:** Retrieves all datasets associated with a specific experiment.
- **Responses:**
  - `200 OK`: A list of associated dataset objects.
  - `404 Not Found`: If the experiment is not found or has no associated datasets.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create Dataset for Experiment

- **Endpoint:** `/id/{experiment_id}/datasets`
- **Method:** `POST`
- **Description:** Creates a new dataset for a specific experiment.
- **Request Body:**
  - `dataset_name`: The name of the dataset.
  - `dataset_info`: Additional information about the dataset.
  - `dataset_type_id`: The ID of the dataset type.
  - `collection_date`: The date when the data was collected.
- **Responses:**
  - `200 OK`: The newly created dataset object.
  - `500 Internal Server Error`: If the dataset cannot be created.
