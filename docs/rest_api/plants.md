# Plants API

The Plants API provides endpoints for managing and retrieving plant data.

## Get All Plants

- **Endpoint:** `/all`
- **Method:** `GET`
- **Description:** Retrieves a list of all plants in the database.
- **Responses:**
  - `200 OK`: A list of plant objects.
  - `404 Not Found`: If no plants are found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Search for Plants

- **Endpoint:** `/`
- **Method:** `GET`
- **Description:** Searches for plants based on the provided criteria.
- **Query Parameters:**
  - `plant_number` (optional): The number of the plant.
  - `plot_number` (optional): The number of the plot.
  - `plot_row_number` (optional): The row number of the plot.
  - `plot_column_number` (optional): The column number of the plot.
  - `population_accession` (optional): The accession number of the population.
  - `population_name` (optional): The population of the population.
  - `experiment_name` (optional): The name of the associated experiment.
  - `season_name` (optional): The name of the season.
  - `site_name` (optional): The name of the site.
  - `plant_info` (optional): Additional information about the plant in JSON format.
- **Responses:**
  - `200 OK`: A list of matching plant objects.
  - `404 Not Found`: If no plants match the search criteria.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Plant by ID

- **Endpoint:** `/id/{plant_id}`
- **Method:** `GET`
- **Description:** Retrieves a specific plant by its unique ID.
- **Path Parameter:**
  - `plant_id`: The ID of the plant to retrieve.
- **Responses:**
  - `200 OK`: The requested plant object.
  - `404 Not Found`: If the plant with the given ID is not found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create a New Plant

- **Endpoint:** `/`
- **Method:** `POST`
- **Description:** Creates a new plant in the database.
- **Request Body:**
  - `plant_number`: The number of the plant.
  - `plant_info`: Additional information about the plant.
  - `population_accession`: The accession number of the population.
  - `population_name`: The population of the population.
  - `experiment_name`: The name of the associated experiment.
  - `season_name`: The name of the season.
  - `site_name`: The name of the site.
  - `plot_number`: The number of the plot.
  - `plot_row_number`: The row number of the plot.
  - `plot_column_number`: The column number of the plot.
- **Responses:**
  - `200 OK`: The newly created plant object.
  - `500 Internal Server Error`: If the plant cannot be created.

## Update an Existing Plant

- **Endpoint:** `/id/{plant_id}`
- **Method:** `PATCH`
- **Description:** Updates an existing plant's information.
- **Path Parameter:**
  - `plant_id`: The ID of the plant to update.
- **Request Body:**
  - `plant_number` (optional): The new number of the plant.
  - `plant_info` (optional): New information about the plant.
- **Responses:**
  - `200 OK`: The updated plant object.
  - `404 Not Found`: If the plant with the given ID is not found.
  - `500 Internal Server Error`: If the plant cannot be updated.

## Delete a Plant

- **Endpoint:** `/id/{plant_id}`
- **Method:** `DELETE`
- **Description:** Deletes a plant from the database.
- **Path Parameter:**
  - `plant_id`: The ID of the plant to delete.
- **Responses:**
  - `200 OK`: If the plant is successfully deleted.
  - `404 Not Found`: If the plant with the given ID is not found.
  - `500 Internal Server Error`: If the plant cannot be deleted.

## Get Plant Population

- **Endpoint:** `/id/{plant_id}/population`
- **Method:** `GET`
- **Description:** Retrieves the population associated with a specific plant.
- **Responses:**
  - `200 OK`: The associated population object.
  - `404 Not Found`: If the plant or its associated population is not found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Associated Plot

- **Endpoint:** `/id/{plant_id}/plot`
- **Method:** `GET`
- **Description:** Retrieves the plot associated with a specific plant.
- **Responses:**
  - `200 OK`: The associated plot object.
  - `404 Not Found`: If the plant or its associated plot is not found.
  - `500 Internal Server Error`: If an error occurs during the process.
