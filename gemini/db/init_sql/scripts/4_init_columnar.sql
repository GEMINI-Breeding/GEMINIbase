-- ------------------------------------------------------------------------------
-- -- Columnar Tables (using Hydra)
-- ------------------------------------------------------------------------------

------------------------------------------------------------------------------
-- Dataset Records Table
------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gemini.dataset_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID,
    dataset_name TEXT,
    dataset_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID,
    experiment_name TEXT,
    season_id UUID,
    season_name TEXT,
    site_id UUID,
    site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
) USING columnar;


ALTER TABLE gemini.dataset_records ADD CONSTRAINT dataset_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, 
    collection_date, 
    dataset_id, 
    dataset_name, 
    experiment_id,
    experiment_name, 
    season_id, 
    season_name,
    site_id,
    site_name
);

CREATE INDEX dataset_records_record_info_idx ON gemini.dataset_records USING GIN (record_info);
------------------------------------------------------------------------------
-- Sensor Records Table
------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gemini.sensor_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID,
    dataset_name TEXT,
    sensor_id UUID,
    sensor_name TEXT,
    sensor_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID,
    experiment_name TEXT,
    season_id UUID,
    season_name TEXT,
    site_id UUID,
    site_name TEXT,
    plot_id UUID,
    plot_number INTEGER,
    plot_row_number INTEGER,
    plot_column_number INTEGER,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
);

ALTER TABLE gemini.sensor_records ADD CONSTRAINT sensor_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, 
    collection_date, 
    sensor_id, 
    sensor_name, 
    dataset_id,
    dataset_name, 
    experiment_id,
    experiment_name, 
    season_id,
    season_name, 
    site_id,
    site_name, 
    plot_id, 
    plot_number, 
    plot_row_number, 
    plot_column_number
);

CREATE INDEX sensor_records_record_info_idx ON gemini.sensor_records USING GIN (record_info);

------------------------------------------------------------------------------
-- Trait Records Table
------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gemini.trait_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID,
    dataset_name TEXT,
    trait_id UUID,
    trait_name TEXT,
    trait_value REAL NOT NULL DEFAULT 0.0,
    experiment_id UUID, 
    experiment_name TEXT,
    season_id UUID,
    season_name TEXT,
    site_id UUID,
    site_name TEXT,
    plot_id UUID,
    plot_number INTEGER,
    plot_row_number INTEGER,
    plot_column_number INTEGER,
    record_info JSONB NOT NULL DEFAULT '{}'
) USING columnar;

ALTER TABLE gemini.trait_records ADD CONSTRAINT trait_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, 
    collection_date, 
    trait_id, 
    trait_name, 
    dataset_id,
    dataset_name, 
    experiment_id,
    experiment_name, 
    season_id,
    season_name, 
    site_id,
    site_name, 
    plot_id, 
    plot_number, 
    plot_row_number, 
    plot_column_number
);

CREATE INDEX trait_records_record_info_idx ON gemini.trait_records USING GIN (record_info);

------------------------------------------------------------------------------
-- Procedure Records Table
------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gemini.procedure_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID,
    dataset_name TEXT,
    procedure_id UUID,
    procedure_name TEXT,
    procedure_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID,
    experiment_name TEXT,
    season_id UUID,
    season_name TEXT,
    site_id UUID,
    site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
) USING columnar;

ALTER TABLE gemini.procedure_records ADD CONSTRAINT procedure_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, 
    collection_date, 
    procedure_id, 
    procedure_name, 
    dataset_id,
    dataset_name, 
    experiment_id,
    experiment_name, 
    season_id,
    season_name, 
    site_id,
    site_name
);

CREATE INDEX procedure_records_record_info_idx ON gemini.procedure_records USING GIN (record_info);

------------------------------------------------------------------------------
-- Script Records Table
------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gemini.script_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID,
    dataset_name TEXT,
    script_id UUID,
    script_name TEXT,
    script_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID,
    experiment_name TEXT,
    season_id UUID,
    season_name TEXT,
    site_id UUID,
    site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
) USING columnar;

ALTER TABLE gemini.script_records ADD CONSTRAINT script_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, 
    collection_date, 
    script_id, 
    script_name, 
    dataset_id,
    dataset_name, 
    experiment_id,
    experiment_name, 
    season_id,
    season_name, 
    site_id,
    site_name
);

CREATE INDEX script_records_record_info_idx ON gemini.script_records USING GIN (record_info);
------------------------------------------------------------------------------
-- Model Records Table
------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gemini.model_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    dataset_id UUID,
    dataset_name TEXT,
    model_id UUID,
    model_name TEXT,
    model_data JSONB NOT NULL DEFAULT '{}',
    experiment_id UUID,
    experiment_name TEXT,
    season_id UUID,
    season_name TEXT,
    site_id UUID,
    site_name TEXT,
    record_file TEXT,
    record_info JSONB NOT NULL DEFAULT '{}'
) USING columnar;

ALTER TABLE gemini.model_records ADD CONSTRAINT model_records_unique UNIQUE NULLS NOT DISTINCT (
    timestamp, 
    collection_date, 
    model_id, 
    model_name, 
    dataset_id,
    dataset_name, 
    experiment_id,
    experiment_name, 
    season_id,
    season_name, 
    site_id,
    site_name
);

CREATE INDEX model_records_record_info_idx ON gemini.model_records USING GIN (record_info);

------------------------------------------------------------------------------
-- Genotype Records Table
-- Each row = one allele call: one variant in one accession within one study
------------------------------------------------------------------------------

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
) USING columnar;

ALTER TABLE gemini.genotype_records ADD CONSTRAINT genotype_records_unique UNIQUE (
    study_id,
    variant_id,
    accession_id
);

CREATE INDEX genotype_records_study_variant_idx ON gemini.genotype_records (study_id, variant_id);
CREATE INDEX genotype_records_study_accession_idx ON gemini.genotype_records (study_id, accession_id);
CREATE INDEX genotype_records_chromosome_idx ON gemini.genotype_records (chromosome);
CREATE INDEX genotype_records_record_info_idx ON gemini.genotype_records USING GIN (record_info);

