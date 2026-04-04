-------------------------------------------------------------------------------
-- Table Definitions
-------------------------------------------------------------------------------

-- Experiments Table
-- Stores information about the experiments, including for GEMINI
CREATE TABLE IF NOT EXISTS gemini.experiments (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_name varchar(255) NOT NULL,
    experiment_info JSONB DEFAULT '{}',
    experiment_start_date DATE DEFAULT NOW(),
    experiment_end_date DATE, -- Value might be replaced by a trigger
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiments_info ON gemini.experiments USING GIN (experiment_info);

ALTER TABLE gemini.experiments ADD CONSTRAINT experiment_unique UNIQUE (experiment_name);
ALTER TABLE gemini.experiments ADD CONSTRAINT experiment_start_date_check CHECK (experiment_start_date <= experiment_end_date);
ALTER TABLE gemini.experiments ADD CONSTRAINT experiment_end_date_check CHECK (experiment_end_date >= experiment_start_date);

-------------------------------------------------------------------------------
-- Seasons Table
-- Each experiment can have multiple seasons
CREATE TABLE IF NOT EXISTS gemini.seasons (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id uuid REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    season_name VARCHAR(255) NOT NULL,
    season_info JSONB DEFAULT '{}',
    season_start_date DATE DEFAULT NOW(),
    season_end_date DATE, -- Value might be replaced by a trigger
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_seasons_info ON gemini.seasons USING GIN (season_info);

ALTER TABLE gemini.seasons ADD CONSTRAINT season_unique UNIQUE (experiment_id, season_name);
ALTER TABLE gemini.seasons ADD CONSTRAINT season_start_date_check CHECK (season_start_date <= season_end_date);
ALTER TABLE gemini.seasons ADD CONSTRAINT season_end_date_check CHECK (season_end_date >= season_start_date);

-------------------------------------------------------------------------------
-- Sites Table
-- Each experiment can have multiple sites
CREATE TABLE IF NOT EXISTS gemini.sites (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_name varchar(255) NOT NULL,
    site_city varchar(255) DEFAULT '',
    site_state varchar(255) DEFAULT '',
    site_country varchar(255) DEFAULT '',
    site_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sites_info ON gemini.sites USING GIN (site_info);

ALTER TABLE gemini.sites ADD CONSTRAINT site_unique UNIQUE (site_name, site_city, site_state, site_country);

-------------------------------------------------------------------------------
-- Populations Table
-- Each experiment can have multiple populations, and they are a combination of accession and population
CREATE TABLE IF NOT EXISTS gemini.populations (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    population_accession VARCHAR(255) NOT NULL,
    population_name VARCHAR(255) NOT NULL,
    population_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_populations_info ON gemini.populations USING GIN (population_info);

ALTER TABLE gemini.populations ADD CONSTRAINT population_unique UNIQUE (population_accession, population_name);

-------------------------------------------------------------------------------
-- Plots Table
-- This is where all the plot information is stored
CREATE TABLE IF NOT EXISTS gemini.plots (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id uuid REFERENCES gemini.experiments(id) ON DELETE SET NULL,
    season_id uuid REFERENCES gemini.seasons(id) ON DELETE SET NULL, 
    site_id uuid REFERENCES gemini.sites(id) ON DELETE SET NULL,
    plot_number INTEGER,
    plot_row_number INTEGER,
    plot_column_number INTEGER,
    plot_geometry_info JSONB DEFAULT '{}',
    plot_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
    

CREATE INDEX IF NOT EXISTS idx_plots_info ON gemini.plots USING GIN (plot_info);

ALTER TABLE gemini.plots ADD CONSTRAINT plot_unique UNIQUE (experiment_id, season_id, site_id, plot_number, plot_row_number, plot_column_number);

-------------------------------------------------------------------------------
-- Plants Table
-- This is where all the plant information is stored
CREATE TABLE IF NOT EXISTS gemini.plants (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    plot_id uuid REFERENCES gemini.plots(id) ON DELETE CASCADE,
    plant_number INTEGER,
    plant_info JSONB DEFAULT '{}',
    population_id uuid REFERENCES gemini.populations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plants_info ON gemini.plants USING GIN (plant_info);

ALTER TABLE gemini.plants ADD CONSTRAINT plant_unique UNIQUE (plot_id, plant_number);


-------------------------------------------------------------------------------
-- Data Types Table
-- This is where we will store all possible Data Types that are compatible with GEMINI
-- Acts like a global enumeration for data types
CREATE TABLE IF NOT EXISTS gemini.data_types (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    data_type_name VARCHAR(255) NOT NULL,
    data_type_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_types_info ON gemini.data_types USING GIN (data_type_info);

ALTER TABLE gemini.data_types ADD CONSTRAINT data_type_unique UNIQUE (data_type_name);

-------------------------------------------------------------------------------
-- Data Formats Table
-- This is where we will store all possible Data Formats that are compatible with GEMINI
-- Stores File Formats
CREATE TABLE IF NOT EXISTS gemini.data_formats (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    data_format_name VARCHAR(255) NOT NULL,
    data_format_mime_type VARCHAR(255) DEFAULT 'application/octet-stream',
    data_format_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_formats_info ON gemini.data_formats USING GIN (data_format_info);

ALTER TABLE gemini.data_formats ADD CONSTRAINT data_format_unique UNIQUE (data_format_name);

-------------------------------------------------------------------------------
-- Trait Levels Table
-- This is where we will store all possible Trait Levels that are compatible with GEMINI
-- Acts like a global enumeration for trait levels
CREATE TABLE IF NOT EXISTS gemini.trait_levels (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    trait_level_name VARCHAR(255) NOT NULL,
    trait_level_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trait_levels_info ON gemini.trait_levels USING GIN (trait_level_info);

ALTER TABLE gemini.trait_levels ADD CONSTRAINT trait_level_unique UNIQUE (trait_level_name);

-------------------------------------------------------------------------------
-- Traits Table
-- This is where all the trait information is stored
CREATE TABLE IF NOT EXISTS gemini.traits (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    trait_name VARCHAR(255) NOT NULL,
    trait_units VARCHAR(255) DEFAULT 'units',
    trait_level_id INTEGER REFERENCES gemini.trait_levels(id) ON DELETE SET NULL DEFAULT 0,
    trait_metrics JSONB DEFAULT '{}',
    trait_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE INDEX IF NOT EXISTS idx_traits_info ON gemini.traits USING GIN (trait_info);

ALTER TABLE gemini.traits ADD CONSTRAINT trait_unique UNIQUE (trait_name);

-------------------------------------------------------------------------------
-- Sensor Types Table
-- This is where we will store all possible Sensor Types that are compatible with GEMINI
-- Acts like a global enumeration for sensor types
CREATE TABLE IF NOT EXISTS gemini.sensor_types (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    sensor_type_name VARCHAR(255) NOT NULL,
    sensor_type_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_types_info ON gemini.sensor_types USING GIN (sensor_type_info);

ALTER TABLE gemini.sensor_types ADD CONSTRAINT sensor_type_unique UNIQUE (sensor_type_name);

-------------------------------------------------------------------------------
-- Platforms Table
-- This is where all the platform information is stored
-- A platform is a collection of sensors

CREATE TABLE IF NOT EXISTS gemini.sensor_platforms (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    sensor_platform_name VARCHAR(255) NOT NULL,
    sensor_platform_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_platforms_info ON gemini.sensor_platforms USING GIN (sensor_platform_info);

ALTER TABLE gemini.sensor_platforms ADD CONSTRAINT sensor_platform_unique UNIQUE (sensor_platform_name);

-------------------------------------------------------------------------------
-- Sensors Table
-- This is where all the sensor information is stored
CREATE TABLE IF NOT EXISTS gemini.sensors (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    sensor_name VARCHAR(255) NOT NULL,
    sensor_type_id INTEGER REFERENCES gemini.sensor_types(id) ON DELETE SET NULL DEFAULT 0,
    sensor_data_type_id INTEGER REFERENCES gemini.data_types(id) ON DELETE SET NULL DEFAULT 0,
    sensor_data_format_id INTEGER REFERENCES gemini.data_formats(id) ON DELETE SET NULL DEFAULT 0,
    sensor_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensors_info ON gemini.sensors USING GIN (sensor_info);

ALTER TABLE gemini.sensors ADD CONSTRAINT sensor_unique UNIQUE (sensor_name);


-------------------------------------------------------------------------------
-- Resources Table
-- This is where all the resource information is stored, you can add a resource
CREATE TABLE IF NOT EXISTS gemini.resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_uri VARCHAR(255),
    resource_file_name VARCHAR(255),
    is_external BOOLEAN DEFAULT FALSE,
    resource_experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE SET NULL DEFAULT NULL,
    resource_data_format_id INTEGER REFERENCES gemini.data_formats(id) DEFAULT 0,
    resource_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resources_info ON gemini.resources USING GIN (resource_info);

ALTER TABLE gemini.resources ADD CONSTRAINT resource_unique UNIQUE (resource_uri, resource_file_name);

-------------------------------------------------------------------------------
-- Scripts Table
-- This is where all the script information is stored, you can add a script
CREATE TABLE IF NOT EXISTS gemini.scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_name VARCHAR(255),
    script_url VARCHAR(255),
    script_extension VARCHAR(255),
    script_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scripts_info ON gemini.scripts USING GIN (script_info);

ALTER TABLE gemini.scripts ADD CONSTRAINT script_unique UNIQUE (script_name, script_url);

-------------------------------------------------------------------------------
-- Script Runs Table
-- This is where all the script run information is stored, you can add a script run
CREATE TABLE IF NOT EXISTS gemini.script_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES gemini.scripts(id) ON DELETE CASCADE,
    script_run_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_script_runs_info ON gemini.script_runs USING GIN (script_run_info);

ALTER TABLE gemini.script_runs ADD CONSTRAINT script_run_unique UNIQUE NULLS NOT DISTINCT (script_id, script_run_info);

-------------------------------------------------------------------------------
-- Models Table
-- This is where all the model information is stored, you can add a model
CREATE TABLE IF NOT EXISTS gemini.models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255),
    model_url VARCHAR(255),
    model_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_models_info ON gemini.models USING GIN (model_info);

ALTER TABLE gemini.models ADD CONSTRAINT model_unique UNIQUE (model_name, model_url);

-------------------------------------------------------------------------------
-- Model Runs Table
-- This is where all the model run information is stored, you can add a model run
CREATE TABLE IF NOT EXISTS gemini.model_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES gemini.models(id) ON DELETE CASCADE,
    model_run_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_runs_info ON gemini.model_runs USING GIN (model_run_info);

ALTER TABLE gemini.model_runs ADD CONSTRAINT model_run_unique UNIQUE NULLS NOT DISTINCT (model_id, model_run_info);

-------------------------------------------------------------------------------
-- Procedures Table
-- This is where all the procedure information is stored, you can add a procedure
CREATE TABLE IF NOT EXISTS gemini.procedures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procedure_name VARCHAR(255),
    procedure_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_procedures_info ON gemini.procedures USING GIN (procedure_info);

ALTER TABLE gemini.procedures ADD CONSTRAINT procedure_unique UNIQUE (procedure_name);

-------------------------------------------------------------------------------
-- Procedure Runs Table
-- This is where all the procedure run information is stored, you can add a procedure run
CREATE TABLE IF NOT EXISTS gemini.procedure_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procedure_id UUID REFERENCES gemini.procedures(id) ON DELETE CASCADE,
    procedure_run_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_procedure_runs_info ON gemini.procedure_runs USING GIN (procedure_run_info);

ALTER TABLE gemini.procedure_runs ADD CONSTRAINT procedure_run_unique UNIQUE NULLS NOT DISTINCT (procedure_id, procedure_run_info);

-------------------------------------------------------------------------------
-- Dataset Types Table
-- This is where all the dataset type information is stored
CREATE TABLE IF NOT EXISTS gemini.dataset_types (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    dataset_type_name VARCHAR(255) NOT NULL,
    dataset_type_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dataset_types_info ON gemini.dataset_types USING GIN (dataset_type_info);

ALTER TABLE gemini.dataset_types ADD CONSTRAINT dataset_type_unique UNIQUE (dataset_type_name);

-------------------------------------------------------------------------------
-- Datasets Table
-- This is where all the dataset information is stored
CREATE TABLE IF NOT EXISTS gemini.datasets(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_date DATE DEFAULT NOW(),
    dataset_name VARCHAR(255),
    dataset_info JSONB DEFAULT '{}',
    dataset_type_id INTEGER REFERENCES gemini.dataset_types(id) ON DELETE SET NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datasets_info ON gemini.datasets USING GIN (dataset_info);

ALTER TABLE gemini.datasets ADD CONSTRAINT dataset_name_unique UNIQUE (dataset_name);

------------------------------------------------------------
-- Create the initial data for the database
------------------------------------------------------------

-- Insert Data Types
INSERT INTO gemini.data_types (id, data_type_name, data_type_info)
VALUES
    (0, 'Default', '{"description": "Default Data Type"}'), -- just values
    (1, 'Text', '{"description": "Text Data Type"}'),
    (2, 'Web', '{"description": "HTML Data Type"}'),
    (3, 'Document', '{"description": "Represents PDF, DOCX, DOC etc"}'),
    (4, 'Image', '{"description": "Image Data Type"}'),
    (5, 'Audio', '{"description": "Audio Data Type"}'),
    (6, 'Video', '{"description": "Video Data Type"}'),
    (7, 'Binary', '{"description": "Binary Data Type"}'),
    (8, 'Other', '{"description": "Other Data Type"}');


-- Make sure the next ID is incremented from the last inserted value
SELECT setval(pg_get_serial_sequence('gemini.data_types', 'id'), 8, true);


-- Insert Data Formats
INSERT INTO gemini.data_formats (id, data_format_name, data_format_mime_type, data_format_info)
VALUES
    (0, 'Default', 'application/octet-stream', '{"description": "Default Data Format"}'),
    (1, 'TXT', 'text/plain', '{"description": "Text Data Format"}'),
    (2, 'JSON', 'application/json', '{"description": "JSON Data Format"}'),
    (3, 'CSV', 'text/csv', '{"description": "CSV Data Format"}'),
    (4, 'TSV', 'text/tab-separated-values', '{"description": "TSV Data Format"}'),
    (5, 'XML', 'application/xml', '{"description": "XML Data Format"}'),
    (6, 'HTML', 'text/html', '{"description": "HTML Data Format"}'),
    (7, 'PDF', 'application/pdf', '{"description": "PDF Data Format"}'),
    (8, 'JPEG', 'image/jpeg', '{"description": "JPEG Data Format"}'),
    (9, 'PNG', 'image/png', '{"description": "PNG Data Format"}'),
    (10, 'GIF', 'image/gif', '{"description": "GIF Data Format"}'),
    (11, 'BMP', 'image/bmp', '{"description": "BMP Data Format"}'),
    (12, 'TIFF', 'image/tiff', '{"description": "TIFF Data Format"}'),
    (13, 'WAV', 'audio/wav', '{"description": "WAV Data Format"}'),
    (14, 'MP3', 'audio/mpeg', '{"description": "MP3 Data Format"}'),
    (15, 'MPEG', 'video/mpeg', '{"description": "MPEG Data Format"}'),
    (16, 'AVI', 'video/x-msvideo', '{"description": "AVI Data Format"}'),
    (17, 'MP4', 'video/mp4', '{"description": "MP4 Data Format"}'),
    (18, 'OGG', 'video/ogg', '{"description": "OGG Data Format"}'),
    (19, 'WEBM', 'video/webm', '{"description": "WEBM Data Format"}'),
    (20, 'NPY', 'application/octet-stream', '{"description": "Numpy Data Format"}');

-- Make sure the next ID is incremented from the last inserted value
SELECT setval(pg_get_serial_sequence('gemini.data_formats', 'id'), 20, true);

-- Insert Trait Levels
INSERT INTO gemini.trait_levels (id, trait_level_name, trait_level_info)
VALUES
    (0, 'Default', '{"description": "Default Trait Level"}'),
    (1, 'Plot', '{"description": "Default Plot Level"}'),
    (2, 'Plant', '{"description": "Default Plant Level"}');

-- Make sure the next ID is incremented from the last inserted value
SELECT setval(pg_get_serial_sequence('gemini.trait_levels', 'id'), 2, true);

-- Insert Predefined Sensor Types
INSERT INTO gemini.sensor_types (id, sensor_type_name, sensor_type_info)
VALUES
    (0, 'Default', '{"description": "Default Sensor Type"}'),
    (1, 'RGB', '{"description": "RGB Sensor"}'),
    (2, 'NIR', '{"description": "NIR Sensor"}'),
    (3, 'Thermal', '{"description": "Thermal Sensor"}'),
    (4, 'Multispectral', '{"description": "Multispectral Sensor"}'),
    (5, 'Weather', '{"description": "Weather Sensor"}'),
    (6, 'GPS', '{"description": "GPS Sensor"}'),
    (7, 'Calibration', '{"description": "Calibration Sensor"}'),
    (8, 'Depth', '{"description": "Depth Sensor"}'),
    (9, 'IMU', '{"description": "IMU Sensor"}'),
    (10, 'Disparity', '{"description": "Disparity Maps Source"}'),
    (11, 'Confidence', '{"description": "Confidence Maps Source"}');

-- Make sure the next ID is incremented from the last inserted value
SELECT setval(pg_get_serial_sequence('gemini.sensor_types', 'id'), 11, true);


-- Insert Dataset Types
INSERT INTO gemini.dataset_types (id, dataset_type_name, dataset_type_info)
VALUES
    (0, 'Default', '{"description": "Default Dataset Type"}'),
    (1, 'Sensor', '{"description": "Sensor Dataset Type"}'),
    (2, 'Trait', '{"description": "Trait Dataset Type"}'),
    (3, 'Procedure', '{"description": "Procedure Dataset Type"}'),
    (4, 'Script', '{"description": "Script Dataset Type"}'),
    (5, 'Model', '{"description": "Model Dataset Type"}'),
    (6, 'Other', '{"description": "Other Dataset Type"}');

-- Make sure the next ID is incremented from the last inserted value
SELECT setval(pg_get_serial_sequence('gemini.dataset_types', 'id'), 6, true);

