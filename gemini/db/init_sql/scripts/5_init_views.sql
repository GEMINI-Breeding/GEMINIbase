-------------------------------------------------------------------------------
-- Views and Materialized Views
-------------------------------------------------------------------------------

-------------------------------------------------------------------------------
-- Datatype Format View
CREATE OR REPLACE VIEW gemini.datatype_formats_view AS
SELECT
    dtf.data_type_id AS data_type_id,
    dt.data_type_name AS data_type_name,
    dt.data_type_info AS data_type_info,
    dtf.data_format_id AS data_format_id,
    df.data_format_name AS data_format_name,
    df.data_format_mime_type AS data_format_mime_type,
    df.data_format_info AS data_format_info
FROM
    gemini.data_type_formats dtf
JOIN gemini.data_types dt ON dtf.data_type_id = dt.id
JOIN gemini.data_formats df ON dtf.data_format_id = df.id;


-------------------------------------------------------------------------------
-- View for plot entity combinations
CREATE OR REPLACE VIEW gemini.valid_plot_combinations_view AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    s.id AS season_id,
    s.season_name AS season_name,
    si.id AS site_id,
    si.site_name AS site_name
FROM gemini.experiments AS e
JOIN gemini.seasons AS s
    ON e.id = s.experiment_id
JOIN gemini.experiment_sites AS es
    ON e.id = es.experiment_id
JOIN gemini.sites AS si
    ON es.site_id = si.id;


-------------------------------------------------------------------------------
-- View for storing valid combinations of datasets, experiments, seasons, and sites
CREATE OR REPLACE VIEW gemini.valid_dataset_combinations_view AS
SELECT
    d.dataset_name,
    e.experiment_name,
    s.season_name,
    si.site_name
FROM gemini.datasets AS d
JOIN gemini.experiment_datasets AS ed
    ON d.id = ed.dataset_id
JOIN gemini.experiments AS e
    ON ed.experiment_id = e.id
JOIN gemini.seasons AS s
    ON e.id = s.experiment_id
JOIN gemini.experiment_sites AS es
    ON e.id = es.experiment_id
JOIN gemini.sites AS si
    ON es.site_id = si.id;

-------------------------------------------------------------------------------
-- View for sensor combinations
CREATE OR REPLACE VIEW gemini.valid_sensor_dataset_combinations_view AS
SELECT
    d.dataset_name,
    se.sensor_name,
    e.experiment_name,
    s.season_name,
    si.site_name
FROM gemini.datasets AS d
JOIN gemini.sensor_datasets AS sd
    ON d.id = sd.dataset_id
JOIN gemini.sensors AS se
    ON sd.sensor_id = se.id
JOIN gemini.experiment_datasets AS ed
    ON d.id = ed.dataset_id
JOIN gemini.experiments AS e
    ON ed.experiment_id = e.id
JOIN gemini.seasons AS s
    ON e.id = s.experiment_id
JOIN gemini.experiment_sites AS es
    ON e.id = es.experiment_id
JOIN gemini.sites AS si
    ON es.site_id = si.id;

-------------------------------------------------------------------------------
-- View for trait combinations
CREATE OR REPLACE VIEW gemini.valid_trait_dataset_combinations_view AS
SELECT
    d.dataset_name,
    t.trait_name,
    e.experiment_name,
    s.season_name,
    si.site_name
FROM gemini.datasets AS d
JOIN gemini.trait_datasets AS td
    ON d.id = td.dataset_id
JOIN gemini.traits AS t
    ON td.trait_id = t.id
JOIN gemini.experiment_datasets AS ed
    ON d.id = ed.dataset_id
JOIN gemini.experiments AS e
    ON ed.experiment_id = e.id
JOIN gemini.seasons AS s
    ON e.id = s.experiment_id
JOIN gemini.experiment_sites AS es
    ON e.id = es.experiment_id
JOIN gemini.sites AS si
    ON es.site_id = si.id;

-------------------------------------------------------------------------------
-- View for procedure combinations
CREATE OR REPLACE VIEW gemini.valid_procedure_dataset_combinations_view AS
SELECT
    d.dataset_name,
    p.procedure_name,
    e.experiment_name,
    s.season_name,
    si.site_name
FROM gemini.datasets AS d
JOIN gemini.procedure_datasets AS pd
    ON d.id = pd.dataset_id
JOIN gemini.procedures AS p
    ON pd.procedure_id = p.id
JOIN gemini.experiment_datasets AS ed
    ON d.id = ed.dataset_id
JOIN gemini.experiments AS e
    ON ed.experiment_id = e.id
JOIN gemini.seasons AS s
    ON e.id = s.experiment_id
JOIN gemini.experiment_sites AS es
    ON e.id = es.experiment_id
JOIN gemini.sites AS si
    ON es.site_id = si.id;

-------------------------------------------------------------------------------
-- View for script combinations
CREATE OR REPLACE VIEW gemini.valid_script_dataset_combinations_view AS
SELECT
    d.dataset_name,
    sc.script_name,
    e.experiment_name,
    s.season_name,
    si.site_name
FROM gemini.datasets AS d
JOIN gemini.script_datasets AS sd
    ON d.id = sd.dataset_id
JOIN gemini.scripts AS sc
    ON sd.script_id = sc.id
JOIN gemini.experiment_datasets AS ed
    ON d.id = ed.dataset_id
JOIN gemini.experiments AS e
    ON ed.experiment_id = e.id
JOIN gemini.seasons AS s
    ON e.id = s.experiment_id
JOIN gemini.experiment_sites AS es
    ON e.id = es.experiment_id
JOIN gemini.sites AS si
    ON es.site_id = si.id;

-------------------------------------------------------------------------------
-- View for model combinations
CREATE OR REPLACE VIEW gemini.valid_model_dataset_combinations_view AS
SELECT
    d.dataset_name,
    m.model_name,
    e.experiment_name,
    s.season_name,
    si.site_name
FROM gemini.datasets AS d
JOIN gemini.model_datasets AS md
    ON d.id = md.dataset_id
JOIN gemini.models AS m
    ON md.model_id = m.id
JOIN gemini.experiment_datasets AS ed
    ON d.id = ed.dataset_id
JOIN gemini.experiments AS e
    ON ed.experiment_id = e.id
JOIN gemini.seasons AS s
    ON e.id = s.experiment_id
JOIN gemini.experiment_sites AS es
    ON e.id = es.experiment_id
JOIN gemini.sites AS si
    ON es.site_id = si.id;


-------------------------------------------------------------------------------
-- View for sites and their associated plots
CREATE OR REPLACE VIEW gemini.site_plot_view AS
SELECT
    s.site_name,
    p.id as plot_id,
    p.plot_number,
    p.plot_row_number,
    p.plot_column_number,
    p.plot_geometry_info,
    p.plot_info
FROM gemini.sites AS s
JOIN gemini.plots AS p
    ON s.id = p.site_id;

-------------------------------------------------------------------------------
-- Plot View — denormalizes experiment, season, site, accession, population
CREATE OR REPLACE VIEW gemini.plot_view
AS
SELECT
    p.id AS plot_id,
    e.id AS experiment_id,
    e.experiment_name,
    s.id AS season_id,
    s.season_name,
    si.id AS site_id,
    si.site_name,
    a.id AS accession_id,
    a.accession_name,
    pop.id AS population_id,
    pop.population_name,
    p.plot_number,
    p.plot_row_number,
    p.plot_column_number,
    p.plot_geometry_info,
    p.plot_info
FROM
    gemini.plots p
LEFT JOIN gemini.experiments e ON p.experiment_id = e.id
LEFT JOIN gemini.seasons s ON p.season_id = s.id
LEFT JOIN gemini.sites si ON p.site_id = si.id
LEFT JOIN gemini.accessions a ON p.accession_id = a.id
LEFT JOIN gemini.populations pop ON p.population_id = pop.id;

-------------------------------------------------------------------------------
-- Plot Accession View — enriches plot view with full accession + population info
CREATE OR REPLACE VIEW gemini.plot_accession_view
AS
SELECT
    pv.plot_id,
    pv.plot_number,
    pv.plot_row_number,
    pv.plot_column_number,
    pv.plot_info,
    pv.plot_geometry_info,
    pv.experiment_id,
    pv.experiment_name,
    pv.season_id,
    pv.season_name,
    pv.site_id,
    pv.site_name,
    a.id AS accession_id,
    a.accession_name,
    a.accession_info,
    pop.id AS population_id,
    pop.population_name,
    pop.population_info
FROM
    gemini.plot_view pv
LEFT JOIN gemini.accessions a ON pv.accession_id = a.id
LEFT JOIN gemini.populations pop ON pv.population_id = pop.id;



-------------------------------------------------------------------------------
-- Materialized View to show Experiment Seasons
CREATE OR REPLACE VIEW gemini.experiment_seasons_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    s.id AS season_id,
    s.season_name AS season_name,
    s.season_start_date AS season_start_date,
    s.season_end_date AS season_end_date,
    s.season_info AS season_info
FROM
    gemini.seasons s
LEFT JOIN gemini.experiments e ON s.experiment_id = e.id;

-------------------------------------------------------------------------------
-- Materialized View to show Experiment Sites
CREATE OR REPLACE VIEW gemini.experiment_sites_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    s.id AS site_id,
    s.site_name AS site_name,
    s.site_city AS site_city,
    s.site_state AS site_state,
    s.site_country AS site_country,
    s.site_info AS site_info
FROM
    gemini.sites s
LEFT JOIN gemini.experiment_sites es ON s.id = es.site_id
LEFT JOIN gemini.experiments e ON es.experiment_id = e.id;

-------------------------------------------------------------------------------
-- Materialized View to show Experiment Seasons
CREATE OR REPLACE VIEW gemini.experiment_traits_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    t.id AS trait_id,
    t.trait_name AS trait_name,
    t.trait_units AS trait_units,
    t.trait_metrics AS trait_metrics,
    t.trait_level_id AS trait_level_id,
    t.trait_info AS trait_info
FROM
    gemini.traits t
LEFT JOIN gemini.experiment_traits et ON t.id = et.trait_id
LEFT JOIN gemini.experiments e ON et.experiment_id = e.id;

--------------------------------------------------------------------------------
-- Materialized View to show Experiment Sensor Platforms
CREATE OR REPLACE VIEW gemini.experiment_sensor_platforms_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    sp.id AS sensor_platform_id,
    sp.sensor_platform_name AS sensor_platform_name,
    sp.sensor_platform_info AS sensor_platform_info
FROM
    gemini.sensor_platforms sp  -- Start from sensor_platforms
LEFT JOIN gemini.experiment_sensor_platforms esp ON sp.id = esp.sensor_platform_id
LEFT JOIN gemini.experiments e ON esp.experiment_id = e.id;


-------------------------------------------------------------------------------
-- Materialized View to show Experiment Sensors

CREATE OR REPLACE VIEW gemini.experiment_sensors_view
AS
SELECT
    s.id AS sensor_id,
    s.sensor_name AS sensor_name,
    s.sensor_type_id AS sensor_type_id,
    s.sensor_data_type_id AS sensor_data_type_id,
    s.sensor_data_format_id AS sensor_data_format_id,
    s.sensor_info AS sensor_info,
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date
FROM
    gemini.sensors s  -- Start from sensors
LEFT JOIN gemini.experiment_sensors es ON s.id = es.sensor_id
LEFT JOIN gemini.experiments e ON es.experiment_id = e.id;


-------------------------------------------------------------------------------
-- View to show Experiment Populations
CREATE OR REPLACE VIEW gemini.experiment_populations_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    c.id AS population_id,
    c.population_name AS population_name,
    c.population_type AS population_type,
    c.species AS species,
    c.population_info AS population_info
FROM
    gemini.populations c
LEFT JOIN gemini.experiment_populations ec ON c.id = ec.population_id
LEFT JOIN gemini.experiments e ON ec.experiment_id = e.id;


-------------------------------------------------------------------------------
-- Materialized View to show Experiment Procedures
CREATE OR REPLACE VIEW gemini.experiment_procedures_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    p.id AS procedure_id,
    p.procedure_name AS procedure_name,
    p.procedure_info AS procedure_info
FROM
    gemini.procedures p  -- Start from procedures
LEFT JOIN gemini.experiment_procedures ep ON p.id = ep.procedure_id
LEFT JOIN gemini.experiments e ON ep.experiment_id = e.id;


-------------------------------------------------------------------------------
-- Materialized View to show Experiment Scripts
CREATE OR REPLACE VIEW gemini.experiment_scripts_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    s.id AS script_id,
    s.script_name AS script_name,
    s.script_url AS script_url,
    s.script_extension AS script_extension,
    s.script_info AS script_info
FROM
    gemini.scripts s -- Start from scripts
LEFT JOIN gemini.experiment_scripts es ON s.id = es.script_id
LEFT JOIN gemini.experiments e ON es.experiment_id = e.id;

-------------------------------------------------------------------------------
-- Materialized View to show Experiment Models
CREATE OR REPLACE VIEW gemini.experiment_models_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    m.id AS model_id,
    m.model_name AS model_name,
    m.model_url AS model_url,
    m.model_info AS model_info
FROM
    gemini.models m -- Start from models
LEFT JOIN gemini.experiment_models em ON m.id = em.model_id
LEFT JOIN gemini.experiments e ON em.experiment_id = e.id;

-------------------------------------------------------------------------------
-- Materialized View to show Experiment Datasets
CREATE OR REPLACE VIEW gemini.experiment_datasets_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    d.id AS dataset_id,
    d.collection_date AS collection_date,
    d.dataset_name AS dataset_name,
    d.dataset_type_id AS dataset_type_id,
    d.dataset_info AS dataset_info
FROM
    gemini.datasets d  -- Start from datasets
LEFT JOIN gemini.experiment_datasets ed ON d.id = ed.dataset_id
LEFT JOIN gemini.experiments e ON ed.experiment_id = e.id;


-------------------------------------------------------------------------------
-- Sensor Datasets View
CREATE OR REPLACE VIEW gemini.sensor_datasets_view
AS
SELECT
    sd.sensor_id,
    s.sensor_name AS sensor_name,
    sd.dataset_id,
    d.dataset_name AS dataset_name,
    d.dataset_info AS dataset_info,
    d.collection_date AS collection_date,
    d.dataset_type_id AS dataset_type_id,
    sd.info AS sensor_dataset_info
FROM
    gemini.sensors s  -- Start from sensors to include those without datasets
LEFT JOIN gemini.sensor_datasets sd ON s.id = sd.sensor_id
LEFT JOIN gemini.datasets d ON sd.dataset_id = d.id;

-------------------------------------------------------------------------------
-- Trait Datasets View
CREATE OR REPLACE VIEW gemini.trait_datasets_view
AS
SELECT
    td.trait_id,
    t.trait_name AS trait_name,
    td.dataset_id,
    d.dataset_name AS dataset_name,
    d.dataset_info AS dataset_info,
    d.collection_date AS collection_date,
    d.dataset_type_id AS dataset_type_id,
    td.info AS trait_dataset_info
FROM
    gemini.traits t  -- Start from traits
LEFT JOIN gemini.trait_datasets td ON t.id = td.trait_id
LEFT JOIN gemini.datasets d ON td.dataset_id = d.id;


-------------------------------------------------------------------------------
-- Procedure Datasets View
CREATE OR REPLACE VIEW gemini.procedure_datasets_view
AS
SELECT
    pd.procedure_id,
    p.procedure_name AS procedure_name,
    pd.dataset_id,
    d.dataset_name AS dataset_name,
    d.dataset_info AS dataset_info,
    d.collection_date AS collection_date,
    d.dataset_type_id AS dataset_type_id,
    pd.info AS procedure_dataset_info
FROM
    gemini.procedures p  -- Start from procedures
LEFT JOIN gemini.procedure_datasets pd ON p.id = pd.procedure_id
LEFT JOIN gemini.datasets d ON pd.dataset_id = d.id;

-------------------------------------------------------------------------------
-- Procedure Runs View
CREATE OR REPLACE VIEW gemini.procedure_runs_view
AS
SELECT
    pr.id AS procedure_run_id,
    pr.procedure_id AS procedure_id,
    p.procedure_name AS procedure_name,
    p.procedure_info AS procedure_info,
    pr.procedure_run_info AS procedure_run_info
FROM
    gemini.procedures p -- Start from procedures
FULL OUTER JOIN gemini.procedure_runs pr ON p.id = pr.procedure_id;


-------------------------------------------------------------------------------
-- Script Datasets View
CREATE OR REPLACE VIEW gemini.script_datasets_view
AS
SELECT
    sd.script_id,
    s.script_name AS script_name,
    sd.dataset_id,
    d.dataset_name AS dataset_name,
    d.dataset_info AS dataset_info,
    d.collection_date AS collection_date,
    d.dataset_type_id AS dataset_type_id,
    sd.info AS script_dataset_info
FROM
    gemini.scripts s  -- Start from scripts
LEFT JOIN gemini.script_datasets sd ON s.id = sd.script_id
LEFT JOIN gemini.datasets d ON sd.dataset_id = d.id;

------------------------------------------------------------------------------
-- Script Runs View
CREATE OR REPLACE VIEW gemini.script_runs_view
AS
SELECT
    sr.id AS script_run_id,
    sr.script_id AS script_id,
    s.script_name AS script_name,
    s.script_url AS script_url,
    s.script_extension AS script_extension,
    s.script_info AS script_info,
    sr.script_run_info AS script_run_info
FROM
    gemini.scripts s -- Start from scripts
FULL OUTER JOIN gemini.script_runs sr ON s.id = sr.script_id; -- Full outer join to include all scripts and all runs


-------------------------------------------------------------------------------
-- Model Datasets View
CREATE OR REPLACE VIEW gemini.model_datasets_view
AS
SELECT
    md.model_id,
    m.model_name AS model_name,
    md.dataset_id,
    d.dataset_name AS dataset_name,
    d.dataset_info AS dataset_info,
    d.collection_date AS collection_date,
    d.dataset_type_id AS dataset_type_id,
    md.info AS model_dataset_info
FROM
    gemini.models m  -- Start from models
LEFT JOIN gemini.model_datasets md ON m.id = md.model_id
LEFT JOIN gemini.datasets d ON md.dataset_id = d.id;


-----------------------------------------------------------------------------------
-- Model Runs View
CREATE OR REPLACE VIEW gemini.model_runs_view
AS
SELECT
    mr.id AS model_run_id,
    mr.model_id AS model_id,
    m.model_name AS model_name,
    m.model_url AS model_url,
    m.model_info AS model_info,
    mr.model_run_info AS model_run_info
FROM
    gemini.models m -- Start from models
FULL OUTER JOIN gemini.model_runs mr ON m.id = mr.model_id;


-------------------------------------------------------------------------------
-- Sensor Platform Sensors View
CREATE OR REPLACE VIEW gemini.sensor_platform_sensors_view
AS
SELECT
    sp.id AS sensor_platform_id,
    sp.sensor_platform_name AS sensor_platform_name,
    sp.sensor_platform_info AS sensor_platform_info,
    s.id AS sensor_id,
    s.sensor_name AS sensor_name,
    s.sensor_type_id AS sensor_type_id,
    s.sensor_data_type_id AS sensor_data_type_id,
    s.sensor_data_format_id AS sensor_data_format_id,
    s.sensor_info AS sensor_info,
    sps.info AS sensor_platform_sensor_info
FROM
    gemini.sensor_platforms sp
FULL OUTER JOIN gemini.sensor_platform_sensors sps ON sp.id = sps.sensor_platform_id
FULL OUTER JOIN gemini.sensors s ON sps.sensor_id = s.id;



    
-------------------------------------------------------------------------------
-- View to show Experiment Genotyping Studies
CREATE OR REPLACE VIEW gemini.experiment_genotyping_studies_view
AS
SELECT
    e.id AS experiment_id,
    e.experiment_name AS experiment_name,
    e.experiment_info AS experiment_info,
    e.experiment_start_date AS experiment_start_date,
    e.experiment_end_date AS experiment_end_date,
    g.id AS study_id,
    g.study_name AS study_name,
    g.study_info AS study_info
FROM
    gemini.genotyping_studies g
LEFT JOIN gemini.experiment_genotyping_studies eg ON g.id = eg.study_id
LEFT JOIN gemini.experiments e ON eg.experiment_id = e.id;


-------------------------------------------------------------------------------
-- IMMV
-------------------------------------------------------------------------------

SET default_table_access_method = 'columnar';
SET max_parallel_workers = 1;

-------------------------------------------------------------------------------
-- Sensor Records IMMV
-------------------------------------------------------------------------------
SELECT pgivm.create_immv('gemini.sensor_records_immv', 'select * from gemini.sensor_records');

-------------------------------------------------------------------------------
-- Trait Records IMMV
-------------------------------------------------------------------------------
SELECT pgivm.create_immv('gemini.trait_records_immv', 'select * from gemini.trait_records');

-------------------------------------------------------------------------------
-- Procedure Records IMMV
-------------------------------------------------------------------------------
SELECT pgivm.create_immv('gemini.procedure_records_immv', 'select * from gemini.procedure_records');

-------------------------------------------------------------------------------
-- Script Records IMMV
-------------------------------------------------------------------------------
SELECT pgivm.create_immv('gemini.script_records_immv', 'select * from gemini.script_records');

-------------------------------------------------------------------------------
-- Model Records IMMV
-------------------------------------------------------------------------------
SELECT pgivm.create_immv('gemini.model_records_immv', 'select * from gemini.model_records');

-------------------------------------------------------------------------------
-- Dataset Records IMMV
-------------------------------------------------------------------------------
SELECT pgivm.create_immv('gemini.dataset_records_immv', 'select * from gemini.dataset_records');


SET max_parallel_workers = DEFAULT;
SET default_table_access_method = 'heap';