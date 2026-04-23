# Getting Started & Installation

## Installation Steps

Install all the prerequisites above before continuing

#### Step 1

Clone the repository and enter the root folder

```
$ git clone https://github.com/GEMINI-Breeding/GEMINIbase.git geminibase
$ cd geminibase
```

#### Step 2

Run poetry installation command to install the `geminibase` CLI (backed by the `gemini` Python package).

```
$ poetry install
```

#### Step 3

Setup the GEMINIbase Pipeline

```
$ geminibase setup --default
```

#### Step 4

Build the Docker containers that make up the GEMINIbase Pipeline

```
$ geminibase build
```

#### Step 5

Start the GEMINIbase Pipeline

```
$ geminibase start
```

## Next Steps

The REST API will be available on http://localhost:7777


