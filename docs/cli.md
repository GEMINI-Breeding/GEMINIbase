# Command Line Interface (CLI)

The GEMINIbase Command Line Interface (CLI) provides a powerful way to manage and interact with the GEMINIbase pipeline directly from your terminal. This document outlines the available commands and their usage.

## Main Commands

These commands are used for general management of the GEMINIbase pipeline.

### `geminibase build`

Builds the GEMINIbase pipeline. This command compiles and prepares all necessary components for deployment.

```bash
geminibase build
```

### `geminibase start`

Starts the GEMINIbase pipeline. This will bring up all the services required for GEMINI to operate.

```bash
geminibase start
```

### `geminibase stop`

Stops the GEMINIbase pipeline. This will shut down all running GEMINIbase services.

```bash
geminibase stop
```

### `geminibase clean`

Cleans the GEMINIbase pipeline. This command removes temporary files and build artifacts.

```bash
geminibase clean
```

### `geminibase reset`

Resets the GEMINIbase pipeline. This command saves current settings and then rebuilds the pipeline, effectively bringing it to a clean, re-initialized state.

```bash
geminibase reset
```

### `geminibase setup`

Sets up the GEMINIbase pipeline. This command saves current settings and rebuilds the pipeline.

```bash
geminibase setup [--default]
```

**Options:**

*   `--default`: Use default settings for the setup.

### `geminibase update`

Updates the GEMINIbase pipeline. This command pulls the latest changes, saves current settings, and then rebuilds the pipeline.

```bash
geminibase update
```

## Settings Commands

These commands are used to manage various configuration settings for the GEMINIbase pipeline. All settings commands are accessed via `geminibase settings <command>`.

### `geminibase settings set-local`

Enables or disables local mode for the GEMINIbase pipeline.

```bash
geminibase settings set-local --enable
geminibase settings set-local --disable
```

**Options:**

*   `--enable`: Enable local mode.
*   `--disable`: Disable local mode.

### `geminibase settings set-debug`

Sets the `GEMINI_DEBUG` flag in the `.env` file.

```bash
geminibase settings set-debug --enable
geminibase settings set-debug --disable
```

**Options:**

*   `--enable`: Enable debug mode.
*   `--disable`: Disable debug mode.

### `geminibase settings set-public-domain`

Sets the `GEMINI_PUBLIC_DOMAIN` in the `.env` file and sets `GEMINI_TYPE` to `public`.

```bash
geminibase settings set-public-domain --domain <your-domain.com>
```

**Options:**

*   `--domain <your-domain.com>`: The domain to set for the GEMINIbase pipeline.

### `geminibase settings set-public-ip`

Sets the `GEMINI_PUBLIC_IP` in the `.env` file and sets `GEMINI_TYPE` to `public`.

```bash
geminibase settings set-public-ip --ip <your-public-ip>
```

**Options:**

*   `--ip <your-public-ip>`: The public IP address to set for the GEMINIbase pipeline.
