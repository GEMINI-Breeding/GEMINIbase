# Plots API

The Plots API provides endpoints for managing and retrieving plot data and their associations.

## Get All Plots

- **Endpoint:** `/all`
- **Method:** `GET`
- **Description:** Retrieves a list of all plots in the database.
- **Responses:**
  - `200 OK`: A list of plot objects.
  - `404 Not Found`: If no plots are found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Search for Plots

- **Endpoint:** `/`
- **Method:** `GET`
- **Description:** Searches for plots based on the provided criteria.
- **Query Parameters:**
  - `plot_number` (optional): The number of the plot.
  - `plot_row_number` (optional): The row number of the plot.
  - `plot_column_number` (optional): The column number of the plot.
  - `experiment_name` (optional): The name of the associated experiment.
  - `season_name` (optional): The name of the season.
  - `site_name` (optional): The name of the site.
- **Responses:**
  - `200 OK`: A list of matching plot objects.
  - `404 Not Found`: If no plots match the search criteria.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Plot by ID

- **Endpoint:** `/id/{plot_id}`
- **Method:** `GET`
- **Description:** Retrieves a specific plot by its unique ID.
- **Path Parameter:**
  - `plot_id`: The ID of the plot to retrieve.
- **Responses:**
  - `200 OK`: The requested plot object.
  - `404 Not Found`: If the plot with the given ID is not found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Create a New Plot

- **Endpoint:** `/`
- **Method:** `POST`
- **Description:** Creates a new plot in the database.
- **Request Body:**
  - `plot_number`: The number of the plot.
  - `plot_row_number`: The row number of the plot.
  - `plot_column_number`: The column number of the plot.
  - `plot_info`: Additional information about the plot.
  - `experiment_name`: The name of the associated experiment.
  - `season_name`: The name of the season.
  - `site_name`: The name of the site.
  - `population_accession`: The accession number of the associated population.
  - `population_name`: The population of the associated population.
- **Responses:**
  - `200 OK`: The newly created plot object.
  - `500 Internal Server Error`: If the plot cannot be created.

## Update an Existing Plot

- **Endpoint:** `/id/{plot_id}`
- **Method:** `PATCH`
- **Description:** Updates an existing plot's information.
- **Path Parameter:**
  - `plot_id`: The ID of the plot to update.
- **Request Body:**
  - `plot_number` (optional): The new number of the plot.
  - `plot_row_number` (optional): The new row number of the plot.
  - `plot_column_number` (optional): The new column number of the plot.
  - `plot_info` (optional): New information about the plot.
  - `plot_geometry_info` (optional): New geometry information for the plot.
- **Responses:**
  - `200 OK`: The updated plot object.
  - `404 Not Found`: If the plot with the given ID is not found.
  - `500 Internal Server Error`: If the plot cannot be updated.

## Delete a Plot

- **Endpoint:** `/id/{plot_id}`
- **Method:** `DELETE`
- **Description:** Deletes a plot from the database.
- **Path Parameter:**
  - `plot_id`: The ID of the plot to delete.
- **Responses:**
  - `200 OK`: If the plot is successfully deleted.
  - `404 Not Found`: If the plot with the given ID is not found.
  - `500 Internal Server Error`: If the plot cannot be deleted.

## Get Plot Populations

- **Endpoint:** `/id/{plot_id}/populations`
- **Method:** `GET`
- **Description:** Retrieves all populations associated with a specific plot.
- **Responses:**
  - `200 OK`: A list of associated population objects.
  - `404 Not Found`: If the plot is not found or has no associated populations.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Plot Experiment

- **Endpoint:** `/id/{plot_id}/experiment`
- **Method:** `GET`
- **Description:** Retrieves the experiment associated with a specific plot.
- **Responses:**
  - `200 OK`: The associated experiment object.
  - `404 Not Found`: If the plot or its associated experiment is not found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Plot Season

- **Endpoint:** `/id/{plot_id}/season`
- **Method:** `GET`
- **Description:** Retrieves the season associated with a specific plot.
- **Responses:**
  - `200 OK`: The associated season object.
  - `404 Not Found`: If the plot or its associated season is not found.
  - `500 Internal Server Error`: If an error occurs during the process.

## Get Plot Site

- **Endpoint:** `/id/{plot_id}/site`
- **Method:** `GET`
- **Description:** Retrieves the site associated with a specific plot.
- **Responses:**
  - `200 OK`: The associated site object.
  - `404 Not Found`: If the plot or its associated site is not found.
  - `500 Internal Server Error`: If an error occurs during the process.
