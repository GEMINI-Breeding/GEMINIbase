-- =============================================================================
-- GEMINI Test Database Initialization
-- Standard PostgreSQL 16 (no Hydra columnar, no pg_ivm)
-- Record tables use heap storage; IMMVs are skipped.
-- =============================================================================

-- Schema & Extensions
CREATE SCHEMA IF NOT EXISTS gemini;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA gemini TO gemini_test;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gemini TO gemini_test;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gemini TO gemini_test;
ALTER DEFAULT PRIVILEGES IN SCHEMA gemini GRANT ALL ON TABLES TO gemini_test;
ALTER DEFAULT PRIVILEGES IN SCHEMA gemini GRANT ALL ON SEQUENCES TO gemini_test;

-- =============================================================================
-- CORE TABLES (from 2_init_schema.sql)
-- =============================================================================

CREATE TABLE IF NOT EXISTS gemini.experiments (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_name varchar(255) NOT NULL,
    experiment_info JSONB DEFAULT '{}',
    experiment_start_date DATE DEFAULT NOW(),
    experiment_end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_experiments_info ON gemini.experiments USING GIN (experiment_info);
ALTER TABLE gemini.experiments ADD CONSTRAINT experiment_unique UNIQUE (experiment_name);

CREATE TABLE IF NOT EXISTS gemini.seasons (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id uuid REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    season_name VARCHAR(255) NOT NULL,
    season_info JSONB DEFAULT '{}',
    season_start_date DATE DEFAULT NOW(),
    season_end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_seasons_info ON gemini.seasons USING GIN (season_info);
ALTER TABLE gemini.seasons ADD CONSTRAINT season_unique UNIQUE (experiment_id, season_name);

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

CREATE TABLE IF NOT EXISTS gemini.lines (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    line_name VARCHAR(255) NOT NULL,
    species VARCHAR(255) DEFAULT '',
    line_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lines_info ON gemini.lines USING GIN (line_info);
ALTER TABLE gemini.lines ADD CONSTRAINT line_unique UNIQUE (line_name);

CREATE TABLE IF NOT EXISTS gemini.accessions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    accession_name VARCHAR(255) NOT NULL,
    line_id uuid REFERENCES gemini.lines(id) ON DELETE SET NULL,
    species VARCHAR(255) DEFAULT '',
    accession_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_accessions_info ON gemini.accessions USING GIN (accession_info);
ALTER TABLE gemini.accessions ADD CONSTRAINT accession_unique UNIQUE (accession_name);

CREATE TABLE IF NOT EXISTS gemini.populations (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    population_name VARCHAR(255) NOT NULL,
    population_type VARCHAR(64) DEFAULT '',
    species VARCHAR(255) DEFAULT '',
    population_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_populations_info ON gemini.populations USING GIN (population_info);
ALTER TABLE gemini.populations ADD CONSTRAINT population_unique UNIQUE (population_name);

-- Variants table (genetic markers/SNPs)
CREATE TABLE IF NOT EXISTS gemini.variants (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    variant_name VARCHAR(255) NOT NULL,
    chromosome INTEGER NOT NULL,
    position FLOAT NOT NULL,
    alleles VARCHAR(50) NOT NULL,
    design_sequence TEXT DEFAULT '',
    variant_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_variants_info ON gemini.variants USING GIN (variant_info);
CREATE INDEX IF NOT EXISTS idx_variants_chromosome ON gemini.variants (chromosome);
ALTER TABLE gemini.variants ADD CONSTRAINT variant_unique UNIQUE (variant_name);

-- Genotyping Studies table (genotyping studies/protocols)
CREATE TABLE IF NOT EXISTS gemini.genotyping_studies (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_name VARCHAR(255) NOT NULL,
    study_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_genotyping_studies_info ON gemini.genotyping_studies USING GIN (study_info);
ALTER TABLE gemini.genotyping_studies ADD CONSTRAINT genotyping_study_unique UNIQUE (study_name);

CREATE TABLE IF NOT EXISTS gemini.plots (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id uuid REFERENCES gemini.experiments(id) ON DELETE SET NULL,
    season_id uuid REFERENCES gemini.seasons(id) ON DELETE SET NULL,
    site_id uuid REFERENCES gemini.sites(id) ON DELETE SET NULL,
    accession_id uuid REFERENCES gemini.accessions(id) ON DELETE SET NULL,
    population_id uuid REFERENCES gemini.populations(id) ON DELETE SET NULL,
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

CREATE TABLE IF NOT EXISTS gemini.data_types (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    data_type_name VARCHAR(255) NOT NULL,
    data_type_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_data_types_info ON gemini.data_types USING GIN (data_type_info);
ALTER TABLE gemini.data_types ADD CONSTRAINT data_type_unique UNIQUE (data_type_name);

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

CREATE TABLE IF NOT EXISTS gemini.trait_levels (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    trait_level_name VARCHAR(255) NOT NULL,
    trait_level_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trait_levels_info ON gemini.trait_levels USING GIN (trait_level_info);
ALTER TABLE gemini.trait_levels ADD CONSTRAINT trait_level_unique UNIQUE (trait_level_name);

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

CREATE TABLE IF NOT EXISTS gemini.sensor_types (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    sensor_type_name VARCHAR(255) NOT NULL,
    sensor_type_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sensor_types_info ON gemini.sensor_types USING GIN (sensor_type_info);
ALTER TABLE gemini.sensor_types ADD CONSTRAINT sensor_type_unique UNIQUE (sensor_type_name);

CREATE TABLE IF NOT EXISTS gemini.sensor_platforms (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    sensor_platform_name VARCHAR(255) NOT NULL,
    sensor_platform_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sensor_platforms_info ON gemini.sensor_platforms USING GIN (sensor_platform_info);
ALTER TABLE gemini.sensor_platforms ADD CONSTRAINT sensor_platform_unique UNIQUE (sensor_platform_name);

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

CREATE TABLE IF NOT EXISTS gemini.scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_name VARCHAR(255),
    script_url VARCHAR(255),
    script_extension VARCHAR(255),
    script_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.scripts ADD CONSTRAINT script_unique UNIQUE (script_name, script_url);

CREATE TABLE IF NOT EXISTS gemini.script_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    script_id UUID REFERENCES gemini.scripts(id) ON DELETE CASCADE,
    script_run_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.script_runs ADD CONSTRAINT script_run_unique UNIQUE NULLS NOT DISTINCT (script_id, script_run_info);

CREATE TABLE IF NOT EXISTS gemini.models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255),
    model_url VARCHAR(255),
    model_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.models ADD CONSTRAINT model_unique UNIQUE (model_name, model_url);

CREATE TABLE IF NOT EXISTS gemini.model_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES gemini.models(id) ON DELETE CASCADE,
    model_run_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.model_runs ADD CONSTRAINT model_run_unique UNIQUE NULLS NOT DISTINCT (model_id, model_run_info);

CREATE TABLE IF NOT EXISTS gemini.procedures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procedure_name VARCHAR(255),
    procedure_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.procedures ADD CONSTRAINT procedure_unique UNIQUE (procedure_name);

CREATE TABLE IF NOT EXISTS gemini.procedure_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procedure_id UUID REFERENCES gemini.procedures(id) ON DELETE CASCADE,
    procedure_run_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.procedure_runs ADD CONSTRAINT procedure_run_unique UNIQUE NULLS NOT DISTINCT (procedure_id, procedure_run_info);

CREATE TABLE IF NOT EXISTS gemini.dataset_types (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    dataset_type_name VARCHAR(255) NOT NULL,
    dataset_type_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.dataset_types ADD CONSTRAINT dataset_type_unique UNIQUE (dataset_type_name);

CREATE TABLE IF NOT EXISTS gemini.datasets(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_date DATE DEFAULT NOW(),
    dataset_name VARCHAR(255),
    dataset_info JSONB DEFAULT '{}',
    dataset_type_id INTEGER REFERENCES gemini.dataset_types(id) ON DELETE SET NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE gemini.datasets ADD CONSTRAINT dataset_name_unique UNIQUE (dataset_name);

-- Seed reference data
INSERT INTO gemini.data_types (id, data_type_name) VALUES
    (0, 'Default'), (1, 'Text'), (2, 'Web'), (3, 'Document'),
    (4, 'Image'), (5, 'Audio'), (6, 'Video'), (7, 'Binary'), (8, 'Other');
SELECT setval(pg_get_serial_sequence('gemini.data_types', 'id'), 8, true);

INSERT INTO gemini.data_formats (id, data_format_name, data_format_mime_type) VALUES
    (0, 'Default', 'application/octet-stream'), (1, 'TXT', 'text/plain'),
    (2, 'JSON', 'application/json'), (3, 'CSV', 'text/csv'),
    (4, 'TSV', 'text/tab-separated-values'), (5, 'XML', 'application/xml'),
    (6, 'HTML', 'text/html'), (7, 'PDF', 'application/pdf'),
    (8, 'JPEG', 'image/jpeg'), (9, 'PNG', 'image/png');
SELECT setval(pg_get_serial_sequence('gemini.data_formats', 'id'), 9, true);

INSERT INTO gemini.trait_levels (id, trait_level_name) VALUES
    (0, 'Default'), (1, 'Plot'), (2, 'Plant');
SELECT setval(pg_get_serial_sequence('gemini.trait_levels', 'id'), 2, true);

INSERT INTO gemini.sensor_types (id, sensor_type_name) VALUES
    (0, 'Default'), (1, 'RGB'), (2, 'NIR'), (3, 'Thermal');
SELECT setval(pg_get_serial_sequence('gemini.sensor_types', 'id'), 3, true);

INSERT INTO gemini.dataset_types (id, dataset_type_name) VALUES
    (0, 'Default'), (1, 'Sensor'), (2, 'Trait'), (3, 'Procedure'),
    (4, 'Script'), (5, 'Model'), (6, 'Other');
SELECT setval(pg_get_serial_sequence('gemini.dataset_types', 'id'), 6, true);

-- =============================================================================
-- ASSOCIATION TABLES (from 3_init_relationships.sql)
-- =============================================================================

CREATE TABLE IF NOT EXISTS gemini.data_type_formats (
    data_type_id INTEGER REFERENCES gemini.data_types(id) ON DELETE CASCADE,
    data_format_id INTEGER REFERENCES gemini.data_formats(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (data_type_id, data_format_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_sites (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    site_id UUID REFERENCES gemini.sites(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, site_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_sensors (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, sensor_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_sensor_platforms (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    sensor_platform_id UUID REFERENCES gemini.sensor_platforms(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, sensor_platform_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_traits (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    trait_id UUID REFERENCES gemini.traits(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, trait_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_populations (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    population_id UUID REFERENCES gemini.populations(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, population_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_datasets (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, dataset_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_models (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    model_id UUID REFERENCES gemini.models(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, model_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_procedures (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    procedure_id UUID REFERENCES gemini.procedures(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, procedure_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_scripts (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    script_id UUID REFERENCES gemini.scripts(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, script_id)
);

CREATE TABLE IF NOT EXISTS gemini.experiment_genotyping_studies (
    experiment_id UUID REFERENCES gemini.experiments(id) ON DELETE CASCADE,
    study_id UUID REFERENCES gemini.genotyping_studies(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (experiment_id, study_id)
);

CREATE TABLE IF NOT EXISTS gemini.population_accessions (
    population_id UUID REFERENCES gemini.populations(id) ON DELETE CASCADE,
    accession_id UUID REFERENCES gemini.accessions(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (population_id, accession_id)
);

CREATE TABLE IF NOT EXISTS gemini.sensor_datasets (
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sensor_id, dataset_id)
);

CREATE TABLE IF NOT EXISTS gemini.trait_datasets (
    trait_id UUID REFERENCES gemini.traits(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trait_id, dataset_id)
);

CREATE TABLE IF NOT EXISTS gemini.trait_sensors (
    trait_id UUID REFERENCES gemini.traits(id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (trait_id, sensor_id)
);

CREATE TABLE IF NOT EXISTS gemini.sensor_platform_sensors (
    sensor_platform_id UUID REFERENCES gemini.sensor_platforms(id) ON DELETE CASCADE,
    sensor_id UUID REFERENCES gemini.sensors(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sensor_platform_id, sensor_id)
);

CREATE TABLE IF NOT EXISTS gemini.model_datasets (
    model_id UUID REFERENCES gemini.models(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (model_id, dataset_id)
);

CREATE TABLE IF NOT EXISTS gemini.script_datasets (
    script_id UUID REFERENCES gemini.scripts(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (script_id, dataset_id)
);

CREATE TABLE IF NOT EXISTS gemini.procedure_datasets (
    procedure_id UUID REFERENCES gemini.procedures(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES gemini.datasets(id) ON DELETE CASCADE,
    info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (procedure_id, dataset_id)
);

-- =============================================================================
-- RECORD TABLES (heap storage, no columnar extension)
-- =============================================================================

CREATE TABLE IF NOT EXISTS gemini.sensor_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID, dataset_name TEXT,
    sensor_id UUID, sensor_name TEXT,
    sensor_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID, experiment_name TEXT,
    season_id UUID, season_name TEXT,
    site_id UUID, site_name TEXT,
    plot_id UUID, plot_number INTEGER, plot_row_number INTEGER, plot_column_number INTEGER,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
);
ALTER TABLE gemini.sensor_records ADD CONSTRAINT sensor_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, collection_date, sensor_id, sensor_name, dataset_id, dataset_name,
    experiment_id, experiment_name, season_id, season_name, site_id, site_name,
    plot_id, plot_number, plot_row_number, plot_column_number
);

CREATE TABLE IF NOT EXISTS gemini.trait_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID, dataset_name TEXT,
    trait_id UUID, trait_name TEXT,
    trait_value REAL NOT NULL DEFAULT 0.0,
    experiment_id UUID, experiment_name TEXT,
    season_id UUID, season_name TEXT,
    site_id UUID, site_name TEXT,
    plot_id UUID, plot_number INTEGER, plot_row_number INTEGER, plot_column_number INTEGER,
    record_info JSONB NOT NULL DEFAULT '{}'
);
ALTER TABLE gemini.trait_records ADD CONSTRAINT trait_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, collection_date, trait_id, trait_name, dataset_id, dataset_name,
    experiment_id, experiment_name, season_id, season_name, site_id, site_name,
    plot_id, plot_number, plot_row_number, plot_column_number
);

CREATE TABLE IF NOT EXISTS gemini.dataset_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID, dataset_name TEXT,
    dataset_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID, experiment_name TEXT,
    season_id UUID, season_name TEXT,
    site_id UUID, site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
);
ALTER TABLE gemini.dataset_records ADD CONSTRAINT dataset_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, collection_date, dataset_id, dataset_name,
    experiment_id, experiment_name, season_id, season_name, site_id, site_name
);

CREATE TABLE IF NOT EXISTS gemini.model_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID, dataset_name TEXT,
    model_id UUID, model_name TEXT,
    model_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID, experiment_name TEXT,
    season_id UUID, season_name TEXT,
    site_id UUID, site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS gemini.procedure_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID, dataset_name TEXT,
    procedure_id UUID, procedure_name TEXT,
    procedure_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID, experiment_name TEXT,
    season_id UUID, season_name TEXT,
    site_id UUID, site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS gemini.script_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID, dataset_name TEXT,
    script_id UUID, script_name TEXT,
    script_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID, experiment_name TEXT,
    season_id UUID, season_name TEXT,
    site_id UUID, site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS gemini.genotype_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID,
    study_name TEXT,
    variant_id UUID,
    variant_name TEXT,
    chromosome INTEGER,
    position FLOAT,
    accession_id UUID,
    accession_name TEXT,
    call_value VARCHAR(10),
    record_info JSONB NOT NULL DEFAULT '{}'
);
ALTER TABLE gemini.genotype_records ADD CONSTRAINT genotype_records_unique UNIQUE (
    study_id,
    variant_id,
    accession_id
);
CREATE INDEX genotype_records_study_variant_idx ON gemini.genotype_records (study_id, variant_id);
CREATE INDEX genotype_records_study_accession_idx ON gemini.genotype_records (study_id, accession_id);
CREATE INDEX genotype_records_chromosome_idx ON gemini.genotype_records (chromosome);
CREATE INDEX genotype_records_record_info_idx ON gemini.genotype_records USING GIN (record_info);

-- Resources table (referenced by some models)
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
ALTER TABLE gemini.resources ADD CONSTRAINT resource_unique UNIQUE (resource_uri, resource_file_name);

-- Jobs table (processing task queue)
CREATE TABLE IF NOT EXISTS gemini.jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    progress FLOAT NOT NULL DEFAULT 0.0,
    progress_detail JSONB,
    parameters JSONB,
    result JSONB,
    error_message VARCHAR(2000),
    experiment_id UUID,
    worker_id VARCHAR(100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON gemini.jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON gemini.jobs (job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_experiment ON gemini.jobs (experiment_id);
CREATE INDEX IF NOT EXISTS idx_jobs_detail ON gemini.jobs USING GIN (progress_detail);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION gemini.filter_genotype_records(
    p_study_names TEXT[] DEFAULT NULL,
    p_variant_names TEXT[] DEFAULT NULL,
    p_accession_names TEXT[] DEFAULT NULL,
    p_chromosomes INTEGER[] DEFAULT NULL
)
RETURNS TABLE (
    "id" UUID,
    "study_id" UUID,
    "study_name" TEXT,
    "variant_id" UUID,
    "variant_name" TEXT,
    "chromosome" INTEGER,
    "position" FLOAT,
    "accession_id" UUID,
    "accession_name" TEXT,
    "call_value" VARCHAR(10),
    "record_info" JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        gr.id,
        gr.study_id,
        gr.study_name,
        gr.variant_id,
        gr.variant_name,
        gr.chromosome,
        gr.position,
        gr.accession_id,
        gr.accession_name,
        gr.call_value,
        gr.record_info
    FROM
        gemini.genotype_records gr
    WHERE
        (p_study_names IS NULL OR array_length(p_study_names, 1) IS NULL OR gr.study_name = ANY(p_study_names))
        AND (p_variant_names IS NULL OR array_length(p_variant_names, 1) IS NULL OR gr.variant_name = ANY(p_variant_names))
        AND (p_accession_names IS NULL OR array_length(p_accession_names, 1) IS NULL OR gr.accession_name = ANY(p_accession_names))
        AND (p_chromosomes IS NULL OR array_length(p_chromosomes, 1) IS NULL OR gr.chromosome = ANY(p_chromosomes));
END;
$$;
