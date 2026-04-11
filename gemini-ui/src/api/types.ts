// =============================================================================
// GEMINI REST API TypeScript Types
// Mirrors the Python Pydantic models from gemini/rest_api/models.py
// =============================================================================

// ---------------------------------------------------------------------------
// Common
// ---------------------------------------------------------------------------

export type ID = string;
export type JSONB = Record<string, unknown>;

// ---------------------------------------------------------------------------
// File Handling
// ---------------------------------------------------------------------------

export interface FileMetadata {
  bucket_name: string;
  object_name: string;
  last_modified: string;
  etag: string;
  size: number;
  content_type?: string;
}

export interface ChunkStatusResponse {
  file_identifier: string;
  uploaded_chunks: number;
  total_chunks: number;
  complete: boolean;
}

export interface PresignedUrlResponse {
  url: string;
  expires_in_seconds: number;
}

export interface PaginatedFileList {
  files: FileMetadata[];
  total_count: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Experiment
// ---------------------------------------------------------------------------

export interface ExperimentInput {
  experiment_name: string;
  experiment_info?: JSONB;
  experiment_start_date?: string;
  experiment_end_date?: string;
}

export interface ExperimentUpdate {
  experiment_name?: string;
  experiment_info?: JSONB;
  experiment_start_date?: string;
  experiment_end_date?: string;
}

export interface ExperimentOutput {
  id?: ID;
  experiment_name: string;
  experiment_info?: JSONB;
  experiment_start_date?: string;
  experiment_end_date?: string;
}

// ---------------------------------------------------------------------------
// Season
// ---------------------------------------------------------------------------

export interface SeasonInput {
  season_name: string;
  season_info?: JSONB;
  season_start_date?: string;
  season_end_date?: string;
  experiment_name?: string;
}

export interface SeasonUpdate {
  season_name?: string;
  season_info?: JSONB;
  season_start_date?: string;
  season_end_date?: string;
}

export interface SeasonOutput {
  id?: ID;
  season_name?: string;
  season_info?: JSONB;
  season_start_date?: string;
  season_end_date?: string;
  experiment_id?: ID;
}

// ---------------------------------------------------------------------------
// Site
// ---------------------------------------------------------------------------

export interface SiteInput {
  site_name: string;
  site_city?: string;
  site_state?: string;
  site_country?: string;
  site_info?: JSONB;
  experiment_name?: string;
}

export interface SiteUpdate {
  site_name?: string;
  site_city?: string;
  site_state?: string;
  site_country?: string;
  site_info?: JSONB;
  experiment_name?: string;
}

export interface SiteOutput {
  id?: ID;
  site_name?: string;
  site_city?: string;
  site_state?: string;
  site_country?: string;
  site_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Population
// ---------------------------------------------------------------------------

export interface PopulationInput {
  population_name: string;
  population_accession?: string;
  population_info?: JSONB;
  experiment_name?: string;
}

export interface PopulationUpdate {
  population_name?: string;
  population_accession?: string;
  population_info?: JSONB;
}

export interface PopulationOutput {
  id?: ID;
  population_name?: string;
  population_accession?: string;
  population_info?: JSONB;
}

// ---------------------------------------------------------------------------
// DataFormat
// ---------------------------------------------------------------------------

export interface DataFormatInput {
  data_format_name: string;
  data_format_mime_type?: string;
  data_format_info?: JSONB;
}

export interface DataFormatUpdate {
  data_format_name?: string;
  data_format_mime_type?: string;
  data_format_info?: JSONB;
}

export interface DataFormatOutput {
  id?: ID;
  data_format_name?: string;
  data_format_mime_type?: string;
  data_format_info?: JSONB;
}

// ---------------------------------------------------------------------------
// DataType
// ---------------------------------------------------------------------------

export interface DataTypeInput {
  data_type_name: string;
  data_type_info?: JSONB;
}

export interface DataTypeUpdate {
  data_type_name?: string;
  data_type_info?: JSONB;
}

export interface DataTypeOutput {
  id?: ID;
  data_type_name?: string;
  data_type_info?: JSONB;
}

// ---------------------------------------------------------------------------
// DatasetType
// ---------------------------------------------------------------------------

export interface DatasetTypeInput {
  dataset_type_name: string;
  dataset_type_info?: JSONB;
}

export interface DatasetTypeUpdate {
  dataset_type_name?: string;
  dataset_type_info?: JSONB;
}

export interface DatasetTypeOutput {
  id?: ID;
  dataset_type_name?: string;
  dataset_type_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Dataset
// ---------------------------------------------------------------------------

export interface DatasetInput {
  dataset_name: string;
  collection_date?: string;
  dataset_info?: JSONB;
  dataset_type_id?: ID;
  experiment_name?: string;
}

export interface DatasetUpdate {
  dataset_name?: string;
  collection_date?: string;
  dataset_info?: JSONB;
  dataset_type_id?: ID;
}

export interface DatasetOutput {
  id?: ID;
  dataset_name?: string;
  collection_date?: string;
  dataset_info?: JSONB;
  dataset_type_id?: ID;
}

// ---------------------------------------------------------------------------
// Model (ML)
// ---------------------------------------------------------------------------

export interface ModelInput {
  model_name: string;
  model_url?: string;
  model_info?: JSONB;
  experiment_name?: string;
}

export interface ModelUpdate {
  model_name?: string;
  model_url?: string;
  model_info?: JSONB;
}

export interface ModelOutput {
  id?: ID;
  model_name?: string;
  model_url?: string;
  model_info?: JSONB;
}

export interface ModelRunInput {
  model_name: string;
  model_run_info?: JSONB;
}

export interface ModelRunOutput {
  id?: ID;
  model_name?: string;
  model_run_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Plant
// ---------------------------------------------------------------------------

export interface PlantInput {
  plant_number: number;
  plant_info?: JSONB;
  population_accession?: string;
  population_name?: string;
  experiment_name?: string;
  season_name?: string;
  site_name?: string;
  plot_number?: number;
  plot_row_number?: number;
  plot_column_number?: number;
}

export interface PlantUpdate {
  plant_number?: number;
  plant_info?: JSONB;
}

export interface PlantOutput {
  id?: ID;
  plot_id?: ID;
  population_id?: ID;
  plant_number: number;
  plant_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Plot
// ---------------------------------------------------------------------------

export interface PlotInput {
  plot_number: number;
  plot_row_number: number;
  plot_column_number: number;
  plot_info?: JSONB;
  plot_geometry_info?: JSONB;
  experiment_name?: string;
  season_name?: string;
  site_name?: string;
  population_accession?: string;
  population_name?: string;
}

export interface PlotUpdate {
  plot_number?: number;
  plot_row_number?: number;
  plot_column_number?: number;
  plot_info?: JSONB;
  plot_geometry_info?: JSONB;
}

export interface PlotOutput {
  id?: ID;
  experiment_id?: ID;
  season_id?: ID;
  site_id?: ID;
  plot_number?: number;
  plot_row_number?: number;
  plot_column_number?: number;
  plot_info?: JSONB;
  plot_geometry_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Procedure
// ---------------------------------------------------------------------------

export interface ProcedureInput {
  procedure_name: string;
  procedure_info?: JSONB;
  experiment_name?: string;
}

export interface ProcedureUpdate {
  procedure_info?: JSONB;
  procedure_name?: string;
}

export interface ProcedureOutput {
  id?: ID;
  procedure_name?: string;
  procedure_info?: JSONB;
}

export interface ProcedureRunInput {
  procedure_name: string;
  procedure_run_info?: JSONB;
}

export interface ProcedureRunOutput {
  id?: ID;
  procedure_name?: string;
  procedure_run_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Script
// ---------------------------------------------------------------------------

export interface ScriptInput {
  script_name: string;
  script_url?: string;
  script_extension?: string;
  script_info?: JSONB;
  experiment_name?: string;
}

export interface ScriptUpdate {
  script_name?: string;
  script_url?: string;
  script_extension?: string;
  script_info?: JSONB;
}

export interface ScriptOutput {
  id?: ID;
  script_name?: string;
  script_url?: string;
  script_extension?: string;
  script_info?: JSONB;
}

export interface ScriptRunInput {
  script_name: string;
  script_run_info?: JSONB;
}

export interface ScriptRunOutput {
  id?: ID;
  script_name?: string;
  script_run_info?: JSONB;
}

// ---------------------------------------------------------------------------
// SensorPlatform
// ---------------------------------------------------------------------------

export interface SensorPlatformInput {
  sensor_platform_name: string;
  sensor_platform_info?: JSONB;
  experiment_name?: string;
}

export interface SensorPlatformUpdate {
  sensor_platform_name?: string;
  sensor_platform_info?: JSONB;
}

export interface SensorPlatformOutput {
  id?: ID;
  sensor_platform_name?: string;
  sensor_platform_info?: JSONB;
}

// ---------------------------------------------------------------------------
// SensorType
// ---------------------------------------------------------------------------

export interface SensorTypeInput {
  sensor_type_name: string;
  sensor_type_info?: JSONB;
}

export interface SensorTypeUpdate {
  sensor_type_name?: string;
  sensor_type_info?: JSONB;
}

export interface SensorTypeOutput {
  id?: ID;
  sensor_type_name?: string;
  sensor_type_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Sensor
// ---------------------------------------------------------------------------

export interface SensorInput {
  sensor_name: string;
  sensor_type_id: ID;
  sensor_data_type_id: ID;
  sensor_data_format_id: ID;
  sensor_info?: JSONB;
  experiment_name?: string;
  sensor_platform_name?: string;
}

export interface SensorUpdate {
  sensor_name?: string;
  sensor_type_id?: ID;
  sensor_data_type_id?: ID;
  sensor_data_format_id?: ID;
  sensor_info?: JSONB;
}

export interface SensorOutput {
  id?: ID;
  sensor_name?: string;
  sensor_type_id?: ID;
  sensor_data_type_id?: ID;
  sensor_data_format_id?: ID;
  sensor_info?: JSONB;
}

// ---------------------------------------------------------------------------
// TraitLevel
// ---------------------------------------------------------------------------

export interface TraitLevelInput {
  trait_level_name: string;
  trait_level_info?: JSONB;
}

export interface TraitLevelUpdate {
  trait_level_name?: string;
  trait_level_info?: JSONB;
}

export interface TraitLevelOutput {
  id?: ID;
  trait_level_name?: string;
  trait_level_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

export interface TraitInput {
  trait_name: string;
  trait_units?: string;
  trait_level_id: ID;
  trait_metrics?: JSONB;
  trait_info?: JSONB;
  experiment_name?: string;
}

export interface TraitUpdate {
  trait_name?: string;
  trait_units?: string;
  trait_level_id?: ID;
  trait_metrics?: JSONB;
  trait_info?: JSONB;
}

export interface TraitOutput {
  id?: ID;
  trait_name?: string;
  trait_units?: string;
  trait_level_id?: ID;
  trait_metrics?: JSONB;
  trait_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Record Types (time-series / columnar data)
// ---------------------------------------------------------------------------

export interface DatasetRecordOutput {
  id?: ID;
  timestamp?: string;
  collection_date?: string;
  dataset_id?: ID;
  dataset_name?: string;
  dataset_data?: JSONB;
  experiment_id?: ID;
  experiment_name?: string;
  season_id?: ID;
  season_name?: string;
  site_id?: ID;
  site_name?: string;
  record_file?: string;
  record_info?: JSONB;
}

export interface SensorRecordOutput {
  id?: ID;
  timestamp?: string;
  collection_date?: string;
  sensor_id?: ID;
  sensor_name?: string;
  sensor_data?: JSONB;
  dataset_id?: ID;
  dataset_name?: string;
  experiment_id?: ID;
  experiment_name?: string;
  season_id?: ID;
  season_name?: string;
  site_id?: ID;
  site_name?: string;
  plot_id?: ID;
  plot_number?: number;
  plot_row_number?: number;
  plot_column_number?: number;
  record_file?: string;
  record_info?: JSONB;
}

export interface TraitRecordOutput {
  id?: ID;
  timestamp?: string;
  collection_date?: string;
  trait_id?: ID;
  trait_name?: string;
  trait_value?: number;
  dataset_id?: ID;
  dataset_name?: string;
  experiment_id?: ID;
  experiment_name?: string;
  season_id?: ID;
  season_name?: string;
  site_id?: ID;
  site_name?: string;
  plot_id?: ID;
  plot_number?: number;
  plot_row_number?: number;
  plot_column_number?: number;
  record_info?: JSONB;
}

export interface ModelRecordOutput {
  id?: ID;
  timestamp?: string;
  collection_date?: string;
  dataset_id?: ID;
  dataset_name?: string;
  model_id?: ID;
  model_name?: string;
  model_data?: JSONB;
  experiment_id?: ID;
  experiment_name?: string;
  season_id?: ID;
  season_name?: string;
  site_id?: ID;
  site_name?: string;
  record_file?: string;
  record_info?: JSONB;
}

export interface ProcedureRecordOutput {
  id?: ID;
  timestamp?: string;
  collection_date?: string;
  dataset_id?: ID;
  dataset_name?: string;
  procedure_id?: ID;
  procedure_name?: string;
  procedure_data?: JSONB;
  experiment_id?: ID;
  experiment_name?: string;
  season_id?: ID;
  season_name?: string;
  site_id?: ID;
  site_name?: string;
  record_file?: string;
  record_info?: JSONB;
}

export interface ScriptRecordOutput {
  id?: ID;
  timestamp?: string;
  collection_date?: string;
  dataset_id?: ID;
  dataset_name?: string;
  script_id?: ID;
  script_name?: string;
  script_data?: JSONB;
  experiment_id?: ID;
  experiment_name?: string;
  season_id?: ID;
  season_name?: string;
  site_id?: ID;
  site_name?: string;
  record_file?: string;
  record_info?: JSONB;
}

export interface GenotypeRecordOutput {
  id?: ID;
  genotype_id?: ID;
  genotype_name?: string;
  variant_id?: ID;
  variant_name?: string;
  chromosome?: number;
  position?: number;
  population_id?: ID;
  population_name?: string;
  population_accession?: string;
  call_value?: string;
  record_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Job
// ---------------------------------------------------------------------------

export interface JobSubmitInput {
  job_type: string;
  parameters?: JSONB;
  experiment_id?: ID;
}

export interface JobOutput {
  id?: ID;
  job_type: string;
  status: string;
  progress: number;
  progress_detail?: JSONB;
  parameters?: JSONB;
  result?: JSONB;
  error_message?: string;
  experiment_id?: ID;
  worker_id?: string;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
  updated_at?: string;
}

// ---------------------------------------------------------------------------
// Variant
// ---------------------------------------------------------------------------

export interface VariantInput {
  variant_name: string;
  chromosome: number;
  position: number;
  alleles: string;
  design_sequence?: string;
  variant_info?: JSONB;
}

export interface VariantBulkInput {
  variants: JSONB[];
}

export interface VariantUpdate {
  variant_name?: string;
  chromosome?: number;
  position?: number;
  alleles?: string;
  design_sequence?: string;
  variant_info?: JSONB;
}

export interface VariantOutput {
  id?: ID;
  variant_name?: string;
  chromosome?: number;
  position?: number;
  alleles?: string;
  design_sequence?: string;
  variant_info?: JSONB;
}

// ---------------------------------------------------------------------------
// Genotype
// ---------------------------------------------------------------------------

export interface GenotypeInput {
  genotype_name: string;
  genotype_info?: JSONB;
  experiment_name?: string;
}

export interface GenotypeUpdate {
  genotype_name?: string;
  genotype_info?: JSONB;
}

export interface GenotypeOutput {
  id?: ID;
  genotype_name?: string;
  genotype_info?: JSONB;
}

export interface GenotypeRecordInput {
  genotype_id?: ID;
  genotype_name?: string;
  variant_id?: ID;
  variant_name?: string;
  chromosome?: number;
  position?: number;
  population_id?: ID;
  population_name?: string;
  population_accession?: string;
  call_value: string;
  record_info?: JSONB;
}

export interface GenotypeRecordBulkInput {
  records: JSONB[];
}

// Record filter types
export interface DatasetRecordFilter {
  start_timestamp?: string;
  end_timestamp?: string;
  dataset_names?: string[];
  experiment_names?: string[];
  season_names?: string[];
  site_names?: string[];
}

export interface SensorRecordFilter {
  start_timestamp?: string;
  end_timestamp?: string;
  sensor_names?: string[];
  dataset_names?: string[];
  experiment_names?: string[];
  season_names?: string[];
  site_names?: string[];
}

export interface TraitRecordFilter {
  start_timestamp?: string;
  end_timestamp?: string;
  trait_names?: string[];
  dataset_names?: string[];
  experiment_names?: string[];
  season_names?: string[];
  site_names?: string[];
}

export interface ModelRecordFilter {
  start_timestamp?: string;
  end_timestamp?: string;
  model_names?: string[];
  dataset_names?: string[];
  experiment_names?: string[];
  season_names?: string[];
  site_names?: string[];
}

export interface ProcedureRecordFilter {
  start_timestamp?: string;
  end_timestamp?: string;
  procedure_names?: string[];
  dataset_names?: string[];
  experiment_names?: string[];
  season_names?: string[];
  site_names?: string[];
}

export interface ScriptRecordFilter {
  start_timestamp?: string;
  end_timestamp?: string;
  script_names?: string[];
  dataset_names?: string[];
  experiment_names?: string[];
  season_names?: string[];
  site_names?: string[];
}

// Job management types
export interface JobStatusUpdate {
  status: string;
  worker_id?: string;
  progress?: number;
  progress_detail?: JSONB;
  result?: JSONB;
  error_message?: string;
}
