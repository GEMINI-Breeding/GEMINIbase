# Populations API

The Populations API provides endpoints for managing and retrieving population data.

## Get All Populations

- **Endpoint:** `/all`
- **Method:** `GET`
- **Description:** Retrieves a list of all populations in the database.
- **Responses:**
  - `200 OK`: A list of population objects.
  - `404 Not Found`: If no populations are found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Search for Populations

- **Endpoint:** `/`
- **Method:** `GET`
- **Description:** Searches for populations based on the provided criteria.
- **Query Parameters:**
  - `population_name` (optional): The name of the population.
  - `population_type` (optional): The type of the population.
  - `species` (optional): The species of the population.
  - `population_info` (optional): Additional information about the population in JSON format.
  - `experiment_name` (optional): The name of the associated experiment.
- **Responses:**
  - `200 OK`: A list of matching population objects.
  - `404 Not Found`: If no populations match the search criteria.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Population by ID

- **Endpoint:** `/id/{population_id}`
- **Method:** `GET`
- **Description:** Retrieves a specific population by its unique ID.
- **Path Parameter:**
  - `population_id`: The ID of the population to retrieve.
- **Responses:**
  - `200 OK`: The requested population object.
  - `404 Not Found`: If the population with the given ID is not found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create a New Population

- **Endpoint:** `/`
- **Method:** `POST`
- **Description:** Creates a new population in the database.
- **Request Body:**
  - `population_name`: The name of the population.
  - `population_type`: The type of the population.
  - `species`: The species of the population.
  - `population_info`: Additional information about the population.
  - `experiment_name`: The name of the associated experiment.
- **Responses:**
  - `200 OK`: The newly created population object.
  - `500 Internal Server Error`: If the population cannot be created.

## Update an Existing Population

- **Endpoint:** `/id/{population_id}`
- **Method:** `PATCH`
- **Description:** Updates an existing population's information.
- **Path Parameter:**
  - `population_id`: The ID of the population to update.
- **Request Body:**
  - `population_name` (optional): The new name of the population.
  - `population_type` (optional): The new type of the population.
  - `species` (optional): The new species of the population.
  - `population_info` (optional): New information about the population.
- **Responses:**
  - `200 OK`: The updated population object.
  - `404 Not Found`: If the population with the given ID is not found.
  - `500 Internal Server Error`: If the population cannot be updated.

## Delete a Population

- **Endpoint:** `/id/{population_id}`
- **Method:** `DELETE`
- **Description:** Deletes a population from the database.
- **Path Parameter:**
  - `population_id`: The ID of the population to delete.
- **Responses:**
  - `200 OK`: If the population is successfully deleted.
  - `404 Not Found`: If the population with the given ID is not found.
  - `500 Internal Server Error`: If the population cannot be deleted.

## Get Associated Experiments

- **Endpoint:** `/id/{population_id}/experiments`
- **Method:** `GET`
- **Description:** Retrieves all experiments associated with a specific population.
- **Path Parameter:**
  - `population_id`: The ID of the population.
- **Responses:**
  - `200 OK`: A list of associated experiment objects.
  - `404 Not Found`: If the population is not found or has no associated experiments.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Associated Plots

- **Endpoint:** `/id/{population_id}/plots`
- **Method:** `GET`
- **Description:** Retrieves all plots associated with a specific population.
- **Path Parameter:**
  - `population_id`: The ID of the population.
- **Responses:**
  - `200 OK`: A list of associated plot objects.
  - `404 Not Found`: If the population is not found or has no associated plots.
  - `500 Internal Server Error`: If an error occurs during the process.

