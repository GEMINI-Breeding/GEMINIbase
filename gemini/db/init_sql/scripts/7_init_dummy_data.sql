-------------------------------------------------------------------------------
-- Dummy data for testing
-------------------------------------------------------------------------------

-- Add Dummy Experiment Data
INSERT INTO gemini.experiments (experiment_name, experiment_info, experiment_start_date, experiment_end_date, created_at, updated_at)
VALUES 
    ('Experiment A', '{"description": "Test experiment A"}', '2023-01-01', '2023-12-31', NOW(), NOW()),
    ('Experiment B', '{"description": "Test experiment B"}', '2024-01-01', '2024-12-31', NOW(), NOW());


-- Add 3 Dummy Seasons per Experiment
INSERT INTO gemini.seasons (experiment_id, season_name, season_info, season_start_date, season_end_date, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), 'Season 1A', '{"description": "Test season 1A"}', '2023-01-01', '2023-03-31', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), 'Season 2A', '{"description": "Test season 2A"}', '2023-04-01', '2023-09-30', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), 'Season 3A', '{"description": "Test season 3A"}', '2023-10-01', '2023-12-31', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), 'Season 1B', '{"description": "Test season 1B"}', '2024-01-01', '2024-03-31', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), 'Season 2B', '{"description": "Test season 2B"}', '2024-04-01', '2024-09-30', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), 'Season 3B', '{"description": "Test season 3B"}', '2024-10-01', '2024-12-31', NOW(), NOW());

-- Add 3 Dummy Sites
INSERT INTO gemini.sites (site_name, site_city, site_state, site_country, site_info, created_at, updated_at)
VALUES
    ('Site A1', 'City A', 'State A', 'Country A', '{"description": "Test site A1"}', NOW(), NOW()),
    ('Site A2', 'City A', 'State A', 'Country A', '{"description": "Test site A2"}', NOW(), NOW()),
    ('Site A3', 'City A', 'State A', 'Country A', '{"description": "Test site A3"}', NOW(), NOW()),
    ('Site B1', 'City B', 'State B', 'Country B', '{"description": "Test site B1"}', NOW(), NOW()),
    ('Site B2', 'City B', 'State B', 'Country B', '{"description": "Test site B2"}', NOW(), NOW()),
    ('Site B3', 'City B', 'State B', 'Country B', '{"description": "Test site B3"}', NOW(), NOW());

-- Add associations to experiment_sites
INSERT INTO gemini.experiment_sites (experiment_id, site_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.sites WHERE site_name = 'Site A1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.sites WHERE site_name = 'Site A2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.sites WHERE site_name = 'Site A3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.sites WHERE site_name = 'Site B1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.sites WHERE site_name = 'Site B2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.sites WHERE site_name = 'Site B3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());
    
-- Add 12 Populations, 3 for each dummy population
INSERT INTO gemini.populations (population_accession, population_name, population_info, created_at, updated_at)
VALUES
    ('Accession A1', 'Population A', '{"description": "Test population A1"}', NOW(), NOW()),
    ('Accession A2', 'Population A', '{"description": "Test population A2"}', NOW(), NOW()),
    ('Accession A3', 'Population A', '{"description": "Test population A3"}', NOW(), NOW()),
    ('Accession B1', 'Population B', '{"description": "Test population B1"}', NOW(), NOW()),
    ('Accession B2', 'Population B', '{"description": "Test population B2"}', NOW(), NOW()),
    ('Accession B3', 'Population B', '{"description": "Test population B3"}', NOW(), NOW());


-- Add associations to experiment_populations
INSERT INTO gemini.experiment_populations (experiment_id, population_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.populations WHERE population_accession = 'Accession A1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.populations WHERE population_accession = 'Accession A2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.populations WHERE population_accession = 'Accession A3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.populations WHERE population_accession = 'Accession B1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.populations WHERE population_accession = 'Accession B2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.populations WHERE population_accession = 'Accession B3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());




-- For each combination of experiment, season, and site, add 20 plots
-- Use an anonymous function to generate plot numbers

DO $$
DECLARE
    exp_id UUID;
    sea_id UUID;
    sit_id UUID;
    plot_number INTEGER;
    plot_row_number INTEGER;
    plot_column_number INTEGER;
    plot_info JSONB;
BEGIN
    FOR exp_id IN SELECT id from gemini.experiments LOOP
        FOR sea_id IN SELECT id FROM gemini.seasons WHERE experiment_id = exp_id LOOP
            FOR sit_id IN SELECT site_id from gemini.experiment_sites WHERE experiment_id = exp_id LOOP
                FOR plot_number IN 1..20 LOOP
                    plot_row_number := (plot_number - 1) / 5 + 1;
                    plot_column_number := (plot_number - 1) % 5 + 1;
                    plot_info := jsonb_build_object('description', 'Test plot ' || plot_number);
                    INSERT INTO gemini.plots (experiment_id, season_id, site_id, plot_number, plot_row_number, plot_column_number, plot_info, created_at, updated_at)
                    VALUES (exp_id, sea_id, sit_id, plot_number, plot_row_number, plot_column_number, plot_info, NOW(), NOW());
                END LOOP;
            END LOOP;
        END LOOP;
    END LOOP;
END $$;


-- For each plot, add 2 plants of random populations, but each plot can only have one kind of population
DO $$
DECLARE
    plot_uuid UUID;
    population_uuid UUID;
    plant_number INTEGER;
BEGIN
    FOR plot_uuid in SELECT id FROM gemini.plots LOOP
        -- Select a random population from the populations table
        SELECT id INTO population_uuid FROM gemini.populations ORDER BY RANDOM() LIMIT 1;
        -- Insert 2 plants for each plot with the same population
        FOR plant_number IN 1..2 LOOP
            INSERT INTO gemini.plants (plot_id, plant_number, plant_info, population_id, created_at, updated_at)
            VALUES (plot_uuid, plant_number, jsonb_build_object('description', 'Test plant ' || plant_number), population_uuid, NOW(), NOW());
        END LOOP;

        -- Insert associated plot_population entry
        INSERT INTO gemini.plot_populations (plot_id, population_id, info, created_at, updated_at)
        VALUES (plot_uuid, population_uuid, '{"description": "Verified association"}', NOW(), NOW());

    END LOOP;
END $$;


-- Add 4 Traits
INSERT INTO gemini.traits(trait_name, trait_units, trait_level_id, trait_metrics, trait_info, created_at, updated_at)
VALUES
    ('Trait A1', 'g/m2', 1, '{"mean": 10, "std_dev": 2}', '{"description": "Test trait A1"}', NOW(), NOW()),
    ('Trait A2', 'ml', 2, '{"mean": 15, "std_dev": 3}', '{"description": "Test trait A2"}', NOW(), NOW()),
    ('Trait B1', 'cm', 1, '{"mean": 20, "std_dev": 4}', '{"description": "Test trait B1"}', NOW(), NOW()),
    ('Trait B2', 'kg', 2, '{"mean": 25, "std_dev": 5}', '{"description": "Test trait B2"}', NOW(), NOW());


-- Add associations to experiment_traits, 3 traits exclusively per experiment
INSERT INTO gemini.experiment_traits (experiment_id, trait_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id from gemini.traits WHERE trait_name = 'Trait A1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id from gemini.traits WHERE trait_name = 'Trait A2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id from gemini.traits WHERE trait_name = 'Trait B1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id from gemini.traits WHERE trait_name = 'Trait B2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());


-- Add Dummy Platforms
INSERT INTO gemini.sensor_platforms (sensor_platform_name, sensor_platform_info, created_at, updated_at)
VALUES
    ('Platform A', '{"description": "Test platform A"}', NOW(), NOW()),
    ('Platform B', '{"description": "Test platform B"}', NOW(), NOW());

-- Create 8 Dummy Sensors of assorted type, data type, and data format
INSERT INTO gemini.sensors (sensor_name, sensor_type_id, sensor_data_type_id, sensor_data_format_id, sensor_info, created_at, updated_at)
VALUES
    ('Sensor A1', 1, 1, 1, '{"description": "Test sensor A1"}', NOW(), NOW()),
    ('Sensor A2', 1, 1, 1, '{"description": "Test sensor A2"}', NOW(), NOW()),
    ('Sensor A3', 1, 1, 1, '{"description": "Test sensor A3"}', NOW(), NOW()),
    ('Sensor B1', 1, 1, 1, '{"description": "Test sensor B1"}', NOW(), NOW()),
    ('Sensor B2', 1, 1, 1, '{"description": "Test sensor B2"}', NOW(), NOW()),
    ('Sensor B3', 1, 1, 1, '{"description": "Test sensor B3"}', NOW(), NOW());


-- For platform A, add sensors A1, A2, A3
-- For platform B, add sensors B1, B2, B3

INSERT INTO gemini.sensor_platform_sensors (sensor_platform_id, sensor_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform A' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor A1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform A' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor A2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform A' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor A3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform B' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor B1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform B' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor B2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform B' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor B3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());


-- Add Platforms to Experiments
INSERT INTO gemini.experiment_sensor_platforms (experiment_id, sensor_platform_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform A' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.sensor_platforms WHERE sensor_platform_name = 'Platform B' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());

-- Add Sensors to Experiments
INSERT INTO gemini.experiment_sensors (experiment_id, sensor_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor A1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor A2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor A3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor B1' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor B2' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.sensors WHERE sensor_name = 'Sensor B3' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());

-- Add 2 internal and 2 external resources for each experiment
INSERT INTO gemini.resources (resource_uri, resource_file_name, is_external, resource_experiment_id, resource_data_format_id, resource_info, created_at, updated_at)
VALUES
    ('/path/to/internal/resource1', 'internal_resource1.txt', FALSE, (SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), 1, '{"description": "Test internal resource 1"}', NOW(), NOW()),
    ('/path/to/internal/resource2', 'internal_resource2.txt', FALSE, (SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), 1, '{"description": "Test internal resource 2"}', NOW(), NOW()),
    ('https://www.google.com', 'external_resource1.txt', TRUE, (SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), 1, '{"description": "Test external resource 1"}', NOW(), NOW()),
    ('https://www.yahoo.com', 'external_resource2.txt', TRUE, (SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), 1, '{"description": "Test external resource 2"}', NOW(), NOW());

-- Add 2 Dummy Scripts
INSERT INTO gemini.scripts (script_name, script_url, script_extension, script_info, created_at, updated_at)
VALUES
    ('Script A', '/path/to/scriptA', 'py', '{"description": "Test script A"}', NOW(), NOW()),
    ('Script B', '/path/to/scriptB', 'py', '{"description": "Test script B"}', NOW(), NOW());

-- Assign Dummy Scripts to Experiments
INSERT INTO gemini.experiment_scripts (experiment_id, script_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.scripts WHERE script_name = 'Script A' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.scripts WHERE script_name = 'Script B' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());

-- Create 10 script runs for each script
DO $$
DECLARE
    script_uuid UUID;
    script_run_info JSONB;
    script_run_count INTEGER;
BEGIN
    FOR script_uuid IN SELECT id FROM gemini.scripts LOOP
        script_run_count := 1 + (random() * 10)::INTEGER;
        FOR i IN 1..script_run_count LOOP
            script_run_info := jsonb_build_object('run_number', i, 'run_info', 'Test run ' || i);
            INSERT INTO gemini.script_runs (script_id, script_run_info, created_at, updated_at)
            VALUES (script_uuid, script_run_info, NOW(), NOW());
        END LOOP;
    END LOOP;
END $$;

-- Add 2 Dummy Models
INSERT INTO gemini.models (model_name, model_url, model_info, created_at, updated_at)
VALUES
    ('Model A', '/path/to/modelA', '{"description": "Test model A"}', NOW(), NOW()),
    ('Model B', '/path/to/modelB', '{"description": "Test model B"}', NOW(), NOW());

-- Assign Dummy Models to Experiments
INSERT INTO gemini.experiment_models (experiment_id, model_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.models WHERE model_name = 'Model A' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.models WHERE model_name = 'Model B' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());

-- Create 10 model runs for each model
DO $$
DECLARE
    model_uuid UUID;
    model_run_info JSONB;
    model_run_count INTEGER;
BEGIN
    FOR model_uuid IN SELECT id FROM gemini.models LOOP
        model_run_count := 1 + (random() * 10)::INTEGER;
        FOR i IN 1..model_run_count LOOP
            model_run_info := jsonb_build_object('run_number', i, 'run_info', 'Test run ' || i);
            INSERT INTO gemini.model_runs (model_id, model_run_info, created_at, updated_at)
            VALUES (model_uuid, model_run_info, NOW(), NOW());
        END LOOP;
    END LOOP;
END $$;

-- Add 2 Dummy Procedures
INSERT INTO gemini.procedures (procedure_name, procedure_info, created_at, updated_at)
VALUES
    ('Procedure A', '{"description": "Test procedure A"}', NOW(), NOW()),
    ('Procedure B', '{"description": "Test procedure B"}', NOW(), NOW());

-- Assign Dummy Procedures to Experiments
INSERT INTO gemini.experiment_procedures (experiment_id, procedure_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.procedures WHERE procedure_name = 'Procedure A' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.procedures WHERE procedure_name = 'Procedure B' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());

-- Create 10 procedure runs for each procedure
DO $$
DECLARE
    procedure_uuid UUID;
    procedure_run_info JSONB;
    procedure_run_count INTEGER;
BEGIN
    FOR procedure_uuid IN SELECT id FROM gemini.procedures LOOP
        procedure_run_count := 1 + (random() * 10)::INTEGER;
        FOR i IN 1..procedure_run_count LOOP
            procedure_run_info := jsonb_build_object('run_number', i, 'run_info', 'Test run ' || i);
            INSERT INTO gemini.procedure_runs (procedure_id, procedure_run_info, created_at, updated_at)
            VALUES (procedure_uuid, procedure_run_info, NOW(), NOW());
        END LOOP;
    END LOOP;
END $$;

-- Add 2 Datasets of Default Dataset Type
INSERT INTO gemini.datasets (dataset_name, dataset_type_id, dataset_info, created_at, updated_at)
VALUES
    ('Dataset A', 0, '{"description": "Test dataset A"}', NOW(), NOW()),
    ('Dataset B', 0, '{"description": "Test dataset B"}', NOW(), NOW());

-- Assign Datasets to Experiments
INSERT INTO gemini.experiment_datasets (experiment_id, dataset_id, info, created_at, updated_at)
VALUES
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment A' LIMIT 1), (SELECT id FROM gemini.datasets WHERE dataset_name = 'Dataset A' LIMIT 1), '{"description": "Test association"}', NOW(), NOW()),
    ((SELECT id FROM gemini.experiments WHERE experiment_name = 'Experiment B' LIMIT 1), (SELECT id FROM gemini.datasets WHERE dataset_name = 'Dataset B' LIMIT 1), '{"description": "Test association"}', NOW(), NOW());

-- For each sensor create a Dataset
DO $$
DECLARE
    sen_name TEXT;
    dat_name TEXT;
    dat_info JSONB;
BEGIN
    FOR sen_name IN SELECT sensor_name FROM gemini.sensors LOOP
        dat_info := jsonb_build_object('description', 'Test dataset for sensor ' || sen_name);
        dat_name := sen_name || ' Dataset';
        INSERT INTO gemini.datasets (dataset_name, dataset_type_id, dataset_info, created_at, updated_at)
        VALUES (dat_name, 1, dat_info, NOW(), NOW());
        INSERT INTO gemini.sensor_datasets (sensor_id, dataset_id, info, created_at, updated_at)
        VALUES ((SELECT id FROM gemini.sensors WHERE sensor_name = sen_name LIMIT 1), (SELECT id FROM gemini.datasets WHERE dataset_name = dat_name LIMIT 1), '{"description": "Test association"}', NOW(), NOW());
    END LOOP;
END $$;

-- Assign Sensor Datasets to Experiments based on experiment_sensors
INSERT INTO gemini.experiment_datasets (experiment_id, dataset_id, info, created_at, updated_at)
SELECT es.experiment_id, sd.dataset_id, '{"description": "Test association"}', NOW(), NOW()
FROM gemini.experiment_sensors es
JOIN gemini.sensor_datasets sd ON es.sensor_id = sd.sensor_id;
    

-- For each trait create a Dataset
DO $$
DECLARE
    tr_name TEXT;
    dat_name TEXT;
    dat_info JSONB;
BEGIN
    FOR tr_name IN SELECT trait_name FROM gemini.traits LOOP
        dat_info := jsonb_build_object('description', 'Test dataset for trait ' || tr_name);
        dat_name := tr_name || ' Dataset';
        INSERT INTO gemini.datasets (dataset_name, dataset_type_id, dataset_info, created_at, updated_at)
        VALUES (dat_name, 2, dat_info, NOW(), NOW());
        INSERT INTO gemini.trait_datasets (trait_id, dataset_id, info, created_at, updated_at)
        VALUES ((SELECT id FROM gemini.traits WHERE trait_name = tr_name LIMIT 1), (SELECT id FROM gemini.datasets WHERE dataset_name = dat_name LIMIT 1), '{"description": "Test association"}', NOW(), NOW());
    END LOOP;
END $$;

-- Assign Trait Datasets to Experiments based on experiment_traits
INSERT INTO gemini.experiment_datasets (experiment_id, dataset_id, info, created_at, updated_at)
SELECT et.experiment_id, td.dataset_id, '{"description": "Test association"}', NOW(), NOW()
FROM gemini.experiment_traits et
JOIN gemini.trait_datasets td ON et.trait_id = td.trait_id;


-- For each model create a Dataset
DO $$
DECLARE
    m_name TEXT;
    dat_name TEXT;
    dat_info JSONB;
BEGIN
    FOR m_name IN SELECT model_name FROM gemini.models LOOP
        dat_info := jsonb_build_object('description', 'Test dataset for model ' || m_name);
        dat_name := m_name || ' Dataset';
        INSERT INTO gemini.datasets (dataset_name, dataset_type_id, dataset_info, created_at, updated_at)
        VALUES (dat_name, 5, dat_info, NOW(), NOW());
        INSERT INTO gemini.model_datasets (model_id, dataset_id, info, created_at, updated_at)
        VALUES ((SELECT id FROM gemini.models WHERE model_name = m_name LIMIT 1), (SELECT id FROM gemini.datasets WHERE dataset_name = dat_name LIMIT 1), '{"description": "Test association"}', NOW(), NOW());
    END LOOP;
END $$;

-- Assign Model Datasets to Experiments based on experiment_models
INSERT INTO gemini.experiment_datasets (experiment_id, dataset_id, info, created_at, updated_at)
SELECT em.experiment_id, md.dataset_id, '{"description": "Test association"}', NOW(), NOW()
FROM gemini.experiment_models em
JOIN gemini.model_datasets md ON em.model_id = md.model_id;


-- For each script create a Dataset
DO $$
DECLARE
    s_name TEXT;
    dat_name TEXT;
    dat_info JSONB;
BEGIN
    FOR s_name IN SELECT script_name FROM gemini.scripts LOOP
        dat_info := jsonb_build_object('description', 'Test dataset for script ' || s_name);
        dat_name := s_name || ' Dataset';
        INSERT INTO gemini.datasets (dataset_name, dataset_type_id, dataset_info, created_at, updated_at)
        VALUES (dat_name, 4, dat_info, NOW(), NOW());
        INSERT INTO gemini.script_datasets (script_id, dataset_id, info, created_at, updated_at)
        VALUES ((SELECT id FROM gemini.scripts WHERE script_name = s_name LIMIT 1), (SELECT id FROM gemini.datasets WHERE dataset_name = dat_name LIMIT 1), '{"description": "Test association"}', NOW(), NOW());
    END LOOP;
END $$;

-- Assign Script Datasets to Experiments based on experiment_scripts
INSERT INTO gemini.experiment_datasets (experiment_id, dataset_id, info, created_at, updated_at)
SELECT es.experiment_id, sd.dataset_id, '{"description": "Test association"}', NOW(), NOW()
FROM gemini.experiment_scripts es
JOIN gemini.script_datasets sd ON es.script_id = sd.script_id;


-- For each procedure create a Dataset
DO $$
DECLARE
    p_name TEXT;
    dat_name TEXT;
    dat_info JSONB;
BEGIN
    FOR p_name IN SELECT procedure_name FROM gemini.procedures LOOP
        dat_info := jsonb_build_object('description', 'Test dataset for procedure ' || p_name);
        dat_name := p_name || ' Dataset';
        INSERT INTO gemini.datasets (dataset_name, dataset_type_id, dataset_info, created_at, updated_at)
        VALUES (dat_name, 3, dat_info, NOW(), NOW());
        INSERT INTO gemini.procedure_datasets (procedure_id, dataset_id, info, created_at, updated_at)
        VALUES ((SELECT id FROM gemini.procedures WHERE procedure_name = p_name LIMIT 1), (SELECT id FROM gemini.datasets WHERE dataset_name = dat_name LIMIT 1), '{"description": "Test association"}', NOW(), NOW());
    END LOOP;
END $$;

-- Assign Procedure Datasets to Experiments based on experiment_procedures
INSERT INTO gemini.experiment_datasets (experiment_id, dataset_id, info, created_at, updated_at)
SELECT ep.experiment_id, pd.dataset_id, '{"description": "Test association"}', NOW(), NOW()
FROM gemini.experiment_procedures ep
JOIN gemini.procedure_datasets pd ON ep.procedure_id = pd.procedure_id;

-- Add 10 records for each valid combination for Default Dataset Type
DO $$
DECLARE
    rec_count INTEGER;
    valid_row RECORD;
    time_offset INTERVAL;
    dataset_data JSONB;
BEGIN
    FOR valid_row IN (SELECT * FROM gemini.valid_dataset_combinations_view WHERE dataset_name IN ('Dataset A', 'Dataset B')) LOOP
        FOR rec_count IN 1..10 LOOP
            -- Generate a random time offset between 0 and 1 hour
            time_offset := rec_count * (random() * INTERVAL '1 hour');
            -- Generate random data for the dataset
            dataset_data := jsonb_build_object('record_number', rec_count, 'data', jsonb_build_object('field1', random() * 100, 'field2', random() * 100, 'field3', random() * 100));

            INSERT INTO gemini.dataset_records (dataset_name, experiment_name, season_name, site_name, timestamp, collection_date, dataset_data, record_info)
            VALUES (
                valid_row.dataset_name,
                valid_row.experiment_name,
                valid_row.season_name,
                valid_row.site_name,
                NOW() + time_offset,
                (NOW() + time_offset)::DATE,
                dataset_data,
                jsonb_build_object('record_number', rec_count, 'insert_timestamp', NOW())
            );
        END LOOP;
    END LOOP;
END $$;

--------------------------------------------------------------------------------------------------------------------------------------------------------------------

-- Add 10 records for each valid combination for Script based datasets
DO $$
DECLARE
    rec_count INTEGER;
    valid_row RECORD;
    time_offset INTERVAL;
    script_data JSONB;
BEGIN
    FOR valid_row IN (SELECT * FROM gemini.valid_script_dataset_combinations_view) LOOP
        FOR rec_count IN 1..10 LOOP
            -- Generate a random time offset between 0 and 1 hour
            time_offset := rec_count * (random() * INTERVAL '1 hour');
            -- Generate random data for the dataset
            script_data := jsonb_build_object('record_number', rec_count, 'data', jsonb_build_object('field1', random() * 100, 'field2', random() * 100, 'field3', random() * 100));

            INSERT INTO gemini.script_records (dataset_name, script_name, experiment_name, season_name, site_name, timestamp, collection_date, script_data, record_info)
            VALUES (
                valid_row.dataset_name,
                valid_row.script_name,
                valid_row.experiment_name,
                valid_row.season_name,
                valid_row.site_name,
                NOW() + time_offset,
                (NOW() + time_offset)::DATE,
                script_data,
                jsonb_build_object('record_number', rec_count, 'insert_timestamp', NOW())
            );
        END LOOP;
    END LOOP;
END $$;

------------------------------------------------------------------------------------------------------------------------------------------------------------------------

-- Add 10 records for each valid combination for Model based datasets
DO $$
DECLARE
    rec_count INTEGER;
    valid_row RECORD;
    time_offset INTERVAL;
    model_data JSONB;
BEGIN
    FOR valid_row IN (SELECT * FROM gemini.valid_model_dataset_combinations_view) LOOP
        FOR rec_count IN 1..10 LOOP
            -- Generate a random time offset between 0 and 1 hour
            time_offset := rec_count * (random() * INTERVAL '1 hour');
            -- Generate random data for the dataset
            model_data := jsonb_build_object('record_number', rec_count, 'data', jsonb_build_object('field1', random() * 100, 'field2', random() * 100, 'field3', random() * 100));
            INSERT INTO gemini.model_records (dataset_name, model_name, experiment_name, season_name, site_name, timestamp, collection_date, model_data, record_info)
            VALUES (
                valid_row.dataset_name,
                valid_row.model_name,
                valid_row.experiment_name,
                valid_row.season_name,
                valid_row.site_name,
                NOW() + time_offset,
                (NOW() + time_offset)::DATE,
                model_data,
                jsonb_build_object('record_number', rec_count, 'insert_timestamp', NOW())
            );
        END LOOP;
    END LOOP;
END $$;

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

-- Add 10 records for each valid combination for Procedure based datasets
DO $$
DECLARE
    rec_count INTEGER;
    valid_row RECORD;
    time_offset INTERVAL;
    procedure_data JSONB;
BEGIN
    FOR valid_row IN (SELECT * FROM gemini.valid_procedure_dataset_combinations_view) LOOP
        FOR rec_count IN 1..10 LOOP
            -- Generate a random time offset between 0 and 1 hour
            time_offset := rec_count * (random() * INTERVAL '1 hour');
            -- Generate random data for the dataset
            procedure_data := jsonb_build_object('record_number', rec_count, 'data', jsonb_build_object('field1', random() * 100, 'field2', random() * 100, 'field3', random() * 100));
            INSERT INTO gemini.procedure_records (dataset_name, procedure_name, experiment_name, season_name, site_name, timestamp, collection_date, procedure_data, record_info)
            VALUES (
                valid_row.dataset_name,
                valid_row.procedure_name,
                valid_row.experiment_name,
                valid_row.season_name,
                valid_row.site_name,
                NOW() + time_offset,
                (NOW() + time_offset)::DATE,
                procedure_data,
                jsonb_build_object('record_number', rec_count, 'insert_timestamp', NOW())
            );
        END LOOP;
    END LOOP;
END $$;


-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Add sensor_records for each valid plot

-- Refresh plot_view materialized view
-- REFRESH MATERIALIZED VIEW gemini.plot_view;

DO $$
DECLARE
    valid_row RECORD;
    exp_name TEXT;
    sea_name TEXT;
    sit_name TEXT;
    valid_plot RECORD;
    time_offset INTERVAL;
    sensor_data JSONB;
    rec_count INTEGER;
BEGIN
    FOR valid_row IN (SELECT * FROM gemini.valid_sensor_dataset_combinations_view) LOOP
        exp_name = valid_row.experiment_name;
        sea_name = valid_row.season_name;
        sit_name = valid_row.site_name;
        
        FOR valid_plot IN (
            SELECT * FROM gemini.plot_view 
            WHERE experiment_name = exp_name 
            AND season_name = sea_name 
            AND site_name = sit_name
        ) LOOP
            FOR rec_count IN 1..10 LOOP
                -- Generate a random time offset between 0 and 1 hour
                time_offset := rec_count * (random() * INTERVAL '1 hour');
                -- Generate random sensor data
                sensor_data := jsonb_build_object(
                    'sensor_value_1', random() * 100,
                    'sensor_value_2', random() * 100,
                    'sensor_value_3', random() * 100
                );
                INSERT INTO gemini.sensor_records (
                    dataset_name,
                    sensor_name,
                    sensor_data,
                    experiment_name,
                    season_name,
                    site_name,
                    plot_number,
                    plot_row_number,
                    plot_column_number,
                    timestamp,
                    collection_date,
                    record_info
                )
                VALUES (
                    valid_row.dataset_name,
                    valid_row.sensor_name,
                    sensor_data,
                    valid_plot.experiment_name,
                    valid_plot.season_name,
                    valid_plot.site_name,
                    valid_plot.plot_number,
                    valid_plot.plot_row_number,
                    valid_plot.plot_column_number,
                    NOW() + time_offset,
                    (NOW() + time_offset)::DATE,
                    jsonb_build_object(
                        'plot_info', valid_plot.plot_info,
                        'insert_timestamp', NOW()
                    )
                );
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Add trait_records for each valid plot

-- Refresh plot_view materialized view
-- REFRESH MATERIALIZED VIEW gemini.plot_view;

DO $$
DECLARE
    valid_row RECORD;
    exp_name TEXT;
    sea_name TEXT;
    sit_name TEXT;
    valid_plot RECORD;
    time_offset INTERVAL;
    sensor_data JSONB;
    rec_count INTEGER;
    trait_value NUMERIC;
BEGIN
    FOR valid_row IN (SELECT * FROM gemini.valid_trait_dataset_combinations_view) LOOP
        exp_name := valid_row.experiment_name;
        sea_name := valid_row.season_name;
        sit_name := valid_row.site_name;

        FOR valid_plot IN (
            SELECT * FROM gemini.plot_view 
            WHERE experiment_name = exp_name 
            AND season_name = sea_name 
            AND site_name = sit_name
        ) LOOP
            FOR rec_count IN 1..10 LOOP
                -- Generate a random time offset between 0 and 1 hour
                time_offset := rec_count * (random() * INTERVAL '1 hour');
                -- Generate random trait data
                trait_value := random() * 100;

                INSERT INTO gemini.trait_records (
                    dataset_id,
                    dataset_name,
                    trait_name,
                    trait_value,
                    experiment_name,
                    season_name,
                    site_name,
                    plot_number,
                    plot_row_number,
                    plot_column_number,
                    timestamp,
                    collection_date,
                    record_info
                )
                VALUES (
                    (SELECT id FROM gemini.datasets WHERE dataset_name = valid_row.dataset_name),
                    valid_row.dataset_name,
                    valid_row.trait_name,
                    trait_value,
                    valid_plot.experiment_name,
                    valid_plot.season_name,
                    valid_plot.site_name,
                    valid_plot.plot_number,
                    valid_plot.plot_row_number,
                    valid_plot.plot_column_number,
                    NOW() + time_offset,
                    (NOW() + time_offset)::DATE,
                    jsonb_build_object(
                        'plot_info', valid_plot.plot_info,
                        'insert_timestamp', NOW()
                    )
                );
            END LOOP;
        END LOOP;
    END LOOP;
END $$;
