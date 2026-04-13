-------------------------------------------------------------------------------
-- Relationships
-------------------------------------------------------------------------------

-------------------------------------------------------------------------------
-- DataType Formats Table
-- This is where all the data type format information is stored
-- Each data type can have multiple formats
CREATE TABLE IF NOT EXISTS gemini.data_type_formats (
    data_type_id INTEGER REFERENCES gemini.data_types(id) ON DELETE CASCADE,
    data_format_id INTEGER REFERENCES gemini.data_formats(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (data_type_id, data_format_id)
);

ALTER TABLE gemini.data_type_formats ADD CONSTRAINT data_type_format_unique UNIQUE (data_type_id, data_format_id);


-------------------------------------------------------------------------------
-- Experiment Sites Table

CREATE TABLE IF NOT EXISTS gemini.experiment_sites (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    site_id UUID REFERENCES gemini.sites(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, site_id)
);

ALTER TABLE gemini.experiment_sites ADD CONSTRAINT experiment_site_unique UNIQUE (experiment_id, site_id);


-------------------------------------------------------------------------------
-- Experiment Sensors Table

CREATE TABLE IF NOT EXISTS gemini.experiment_sensors (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, sensor_id)
);

ALTER TABLE gemini.experiment_sensors ADD CONSTRAINT experiment_sensor_unique UNIQUE (experiment_id, sensor_id);

-------------------------------------------------------------------------------
-- Experiment Sensor Platforms Table

CREATE TABLE IF NOT EXISTS gemini.experiment_sensor_platforms (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    sensor_platform_id UUID REFERENCES gemini.sensor_platforms(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, sensor_platform_id)
);

ALTER TABLE gemini.experiment_sensor_platforms ADD CONSTRAINT experiment_sensor_platform_unique UNIQUE (experiment_id, sensor_platform_id);

-------------------------------------------------------------------------------
-- Experiment Traits Table

CREATE TABLE IF NOT EXISTS gemini.experiment_traits (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    trait_id UUID REFERENCES gemini.traits(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, trait_id)
);

ALTER TABLE gemini.experiment_traits ADD CONSTRAINT experiment_trait_unique UNIQUE (experiment_id, trait_id);

-------------------------------------------------------------------------------
-- Experiment Populations Table

CREATE TABLE IF NOT EXISTS gemini.experiment_populations (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    population_id UUID REFERENCES gemini.populations(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, population_id)
);

ALTER TABLE gemini.experiment_populations ADD CONSTRAINT experiment_population_unique UNIQUE (experiment_id, population_id);

-------------------------------------------------------------------------------
-- Experiment Datasets Table

CREATE TABLE IF NOT EXISTS gemini.experiment_datasets (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, dataset_id)
);

ALTER TABLE gemini.experiment_datasets ADD CONSTRAINT experiment_dataset_unique UNIQUE (experiment_id, dataset_id);

-------------------------------------------------------------------------------
-- Experiment Models Table

CREATE TABLE IF NOT EXISTS gemini.experiment_models (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    model_id UUID REFERENCES gemini.models(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, model_id)
);

ALTER TABLE gemini.experiment_models ADD CONSTRAINT experiment_model_unique UNIQUE (experiment_id, model_id);

-------------------------------------------------------------------------------
-- Experiment Procedures Table

CREATE TABLE IF NOT EXISTS gemini.experiment_procedures (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    procedure_id UUID REFERENCES gemini.procedures(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, procedure_id)
);

ALTER TABLE gemini.experiment_procedures ADD CONSTRAINT experiment_procedure_unique UNIQUE (experiment_id, procedure_id);

-------------------------------------------------------------------------------
-- Experiment Scripts Table

CREATE TABLE IF NOT EXISTS gemini.experiment_scripts (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    script_id UUID REFERENCES gemini.scripts(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, script_id)
);

ALTER TABLE gemini.experiment_scripts ADD CONSTRAINT experiment_script_unique UNIQUE (experiment_id, script_id);

-------------------------------------------------------------------------------
-- Population Accessions Table (M:M)

CREATE TABLE IF NOT EXISTS gemini.population_accessions (
    population_id UUID REFERENCES gemini.populations(id) ON DELETE CASCADE,
    accession_id UUID REFERENCES gemini.accessions(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (population_id, accession_id)
);

ALTER TABLE gemini.population_accessions ADD CONSTRAINT population_accession_unique UNIQUE (population_id, accession_id);

-------------------------------------------------------------------------------
-- Trait Sensors Table

CREATE TABLE IF NOT EXISTS gemini.trait_sensors (
    trait_id UUID REFERENCES gemini.traits(id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trait_id, sensor_id)
);

ALTER TABLE gemini.trait_sensors ADD CONSTRAINT trait_sensor_unique UNIQUE (trait_id, sensor_id);

-------------------------------------------------------------------------------
-- Sensor Platforms Sensors Table

CREATE TABLE IF NOT EXISTS gemini.sensor_platform_sensors (
    sensor_platform_id UUID REFERENCES gemini.sensor_platforms(id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sensor_platform_id, sensor_id)
);

ALTER TABLE gemini.sensor_platform_sensors ADD CONSTRAINT sensor_platform_sensor_unique UNIQUE (sensor_platform_id, sensor_id);
-------------------------------------------------------------------------------
-- Sensor Datasets Table

CREATE TABLE IF NOT EXISTS gemini.sensor_datasets (
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sensor_id, dataset_id)
);

ALTER TABLE gemini.sensor_datasets ADD CONSTRAINT sensor_dataset_unique UNIQUE (sensor_id, dataset_id);

-------------------------------------------------------------------------------
-- Trait Datasets Table

CREATE TABLE IF NOT EXISTS gemini.trait_datasets (
    trait_id UUID REFERENCES gemini.traits(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trait_id, dataset_id)
);

ALTER TABLE gemini.trait_datasets ADD CONSTRAINT trait_dataset_unique UNIQUE (trait_id, dataset_id);
-------------------------------------------------------------------------------
-- Model Datasets Table

CREATE TABLE IF NOT EXISTS gemini.model_datasets (
    model_id UUID REFERENCES gemini.models(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (model_id, dataset_id)
);

ALTER TABLE gemini.model_datasets ADD CONSTRAINT model_dataset_unique UNIQUE (model_id, dataset_id);

-------------------------------------------------------------------------------
-- Script Datasets Table

CREATE TABLE IF NOT EXISTS gemini.script_datasets (
    script_id UUID REFERENCES gemini.scripts(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (script_id, dataset_id)
);

ALTER TABLE gemini.script_datasets ADD CONSTRAINT script_dataset_unique UNIQUE (script_id, dataset_id);


-------------------------------------------------------------------------------
-- Procedure Datasets Table

CREATE TABLE IF NOT EXISTS gemini.procedure_datasets (
    procedure_id UUID REFERENCES gemini.procedures(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (procedure_id, dataset_id)
);

ALTER TABLE gemini.procedure_datasets ADD CONSTRAINT procedure_dataset_unique UNIQUE (procedure_id, dataset_id);

-------------------------------------------------------------------------------
-- Experiment Genotyping Studies Table

CREATE TABLE IF NOT EXISTS gemini.experiment_genotyping_studies (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    study_id UUID REFERENCES gemini.genotyping_studies(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, study_id)
);

ALTER TABLE gemini.experiment_genotyping_studies ADD CONSTRAINT experiment_genotyping_study_unique UNIQUE (experiment_id, study_id);

-- Create Datatype Formats associations
INSERT INTO gemini.data_type_formats (data_type_id, data_format_id)
VALUES
    (0, 0), -- Default
    (1, 1), -- Text
    (1, 2), -- JSON
    (1, 3), -- CSV
    (1, 4), -- TSV
    (1, 5), -- XML
    (2, 6), -- HTML
    (3, 7), -- PDF
    (4, 8), -- JPEG
    (4, 9), -- PNG
    (4, 10), -- GIF
    (4, 11), -- BMP
    (4, 12), -- TIFF
    (5, 13), -- WAV
    (5, 14), -- MP3
    (6, 15), -- MPEG
    (6, 16), -- AVI
    (6, 17), -- MP4
    (6, 18), -- OGG
    (6, 19), -- WEBM
    (8, 20); -- Other
