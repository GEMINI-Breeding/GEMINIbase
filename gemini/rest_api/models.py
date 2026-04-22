from pydantic import BaseModel, ValidationError, ConfigDict, GetCoreSchemaHandler
from pydantic.types import UUID4
from pydantic.functional_validators import BeforeValidator
from litestar.datastructures import UploadFile
from pydantic_core import core_schema
from typing import Any, List, Union, Optional
from typing_extensions import Annotated
from uuid import UUID
from datetime import datetime
import json


# Pydantic 2.11+ needs an explicit core schema for UploadFile
# since it's a third-party type that Pydantic can't introspect.
def _upload_file_get_pydantic_core_schema(
    _source_type: Any, _handler: GetCoreSchemaHandler
) -> core_schema.CoreSchema:
    return core_schema.no_info_plain_validator_function(
        lambda v: v,
        serialization=core_schema.plain_serializer_function_ser_schema(
            lambda v: str(v), info_arg=False
        ),
    )


# Monkey-patch UploadFile so Pydantic can handle it in model fields
if not hasattr(UploadFile, "__get_pydantic_core_schema__"):
    UploadFile.__get_pydantic_core_schema__ = classmethod(
        staticmethod(_upload_file_get_pydantic_core_schema)
    )

def str_to_dict(value: Any) -> dict:
    if isinstance(value, str):
        return json.loads(value)
    return value

JSONB = Annotated[Union[str, dict], BeforeValidator(str_to_dict)]
ID = Union[int, str, UUID]

# Base Model class for all litestar controllers
class RESTAPIBase(BaseModel):

    model_config = ConfigDict(
        protected_namespaces=(),
        arbitrary_types_allowed=True,
        from_attributes=True,
    )

# --------------------------------
# Error Classes
# --------------------------------
class RESTAPIError(RESTAPIBase):
    error: str
    error_description: str

    def to_html(self):
        return f"<h1>{self.error}</h1><p>{self.error_description}</p>"
    

# --------------------------------
# Paginated Response
# --------------------------------

class PaginatedResponseBase(RESTAPIBase):
    total_records: int
    total_pages: int
    current_page: int
    next_page: Optional[str] = None
    previous_page: Optional[str] = None

# --------------------------------
# File Handling
# --------------------------------

class FileMetadata(RESTAPIBase):
    bucket_name: str
    object_name: str
    last_modified: datetime
    etag: str
    size: int
    content_type: Optional[str] = None

class UploadFileRequest(RESTAPIBase):
    file: UploadFile
    bucket_name: Optional[str] = None
    object_name: Optional[str] = None

class ChunkUploadRequest(RESTAPIBase):
    file_chunk: UploadFile
    chunk_index: int
    total_chunks: int
    file_identifier: str
    object_name: str
    bucket_name: Optional[str] = None

class ChunkStatusResponse(RESTAPIBase):
    file_identifier: str
    uploaded_chunks: int
    total_chunks: int
    complete: bool

class PresignedUrlResponse(RESTAPIBase):
    url: str
    expires_in_seconds: int

class PaginatedFileList(RESTAPIBase):
    files: List[FileMetadata]
    total_count: int
    limit: int
    offset: int


# --------------------------------
# Experiment Classes
# --------------------------------

class ExperimentInput(RESTAPIBase):
    experiment_name: str
    experiment_info: Optional[JSONB] = {}
    experiment_start_date: Optional[datetime] = None
    experiment_end_date: Optional[datetime] = None

class ExperimentUpdate(RESTAPIBase):
    experiment_name: Optional[str] = None
    experiment_info: Optional[JSONB] = None
    experiment_start_date: Optional[datetime] = None
    experiment_end_date: Optional[datetime] = None

class ExperimentSearch(RESTAPIBase):
    experiment_name: Optional[str] = None
    experiment_info: Optional[JSONB] = None
    experiment_start_date: Optional[datetime] = None
    experiment_end_date: Optional[datetime] = None

class ExperimentOutput(RESTAPIBase):
    id: Optional[ID] = None
    experiment_name: str = None
    experiment_info: Optional[JSONB] = None
    experiment_start_date: Optional[datetime] = None
    experiment_end_date: Optional[datetime] = None



# --------------------------------
# Season Classes
# --------------------------------

class SeasonInput(RESTAPIBase):
    season_name: str
    season_info: Optional[JSONB] = {}
    season_start_date: Optional[datetime] = None
    season_end_date: Optional[datetime] = None
    experiment_name: Optional[str] = None

class SeasonUpdate(RESTAPIBase):
    season_name: Optional[str] = None
    season_info: Optional[JSONB] = None
    season_start_date: Optional[datetime] = None
    season_end_date: Optional[datetime] = None

class SeasonSearch(RESTAPIBase):
    season_name: Optional[str] = None
    season_info: Optional[JSONB] = None
    season_start_date: Optional[datetime] = None
    season_end_date: Optional[datetime] = None
    experiment_name: Optional[str] = None

class SeasonOutput(RESTAPIBase):
    id: Optional[ID] = None
    season_name: Optional[str] = None
    season_info: Optional[JSONB] = None
    season_start_date: Optional[datetime] = None
    season_end_date: Optional[datetime] = None
    experiment_id: Optional[ID] = None



# --------------------------------
# Site Classes
# --------------------------------

class SiteInput(RESTAPIBase):
    site_name: str
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    site_country: Optional[str] = None
    site_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class SiteUpdate(RESTAPIBase):
    site_name: Optional[str] = None
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    site_country: Optional[str] = None
    site_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None

class SiteSearch(RESTAPIBase):
    site_name: Optional[str] = None
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    site_country: Optional[str] = None
    site_info: Optional[JSONB] = None

class SiteOutput(RESTAPIBase):
    id: Optional[ID] = None
    site_name: Optional[str] = None
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    site_country: Optional[str] = None
    site_info: Optional[JSONB] = None

# --------------------------------
# Population Classes
# --------------------------------

class PopulationInput(RESTAPIBase):
    population_name: str
    population_type: Optional[str] = None
    species: Optional[str] = None
    population_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class PopulationUpdate(RESTAPIBase):
    population_name: Optional[str] = None
    population_type: Optional[str] = None
    species: Optional[str] = None
    population_info: Optional[JSONB] = None

class PopulationSearch(RESTAPIBase):
    population_name: Optional[str] = None
    population_type: Optional[str] = None
    species: Optional[str] = None
    population_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None

class PopulationOutput(RESTAPIBase):
    id: Optional[ID] = None
    population_name: Optional[str] = None
    population_type: Optional[str] = None
    species: Optional[str] = None
    population_info: Optional[JSONB] = None



# --------------------------------
# Data Format Classes
# --------------------------------

class DataFormatInput(RESTAPIBase):
    data_format_name: str
    data_format_mime_type: Optional[str] = None
    data_format_info: Optional[JSONB] = {}

class DataFormatUpdate(RESTAPIBase):
    data_format_name: Optional[str] = None
    data_format_mime_type: Optional[str] = None
    data_format_info: Optional[JSONB] = None

class DataFormatSearch(RESTAPIBase):
    data_format_name: Optional[str] = None
    data_format_mime_type: Optional[str] = None
    data_format_info: Optional[JSONB] = None

class DataFormatOutput(RESTAPIBase):
    id: Optional[ID] = None
    data_format_name: Optional[str] = None
    data_format_mime_type: Optional[str] = None
    data_format_info: Optional[JSONB] = None



# --------------------------------
# Data Type Classes
# --------------------------------

class DataTypeInput(RESTAPIBase):
    data_type_name: str
    data_type_info: Optional[JSONB] = {}

class DataTypeUpdate(RESTAPIBase):
    data_type_name: Optional[str] = None
    data_type_info: Optional[JSONB] = None

class DataTypeSearch(RESTAPIBase):
    data_type_name: Optional[str] = None
    data_type_info: Optional[JSONB] = None

class DataTypeOutput(RESTAPIBase):
    id: Optional[ID] = None
    data_type_name: Optional[str] = None
    data_type_info: Optional[JSONB] = None


# --------------------------------
# Dataset Type Classes
# --------------------------------

class DatasetTypeInput(RESTAPIBase):
    dataset_type_name: str
    dataset_type_info: Optional[JSONB] = {}

class DatasetTypeUpdate(RESTAPIBase):
    dataset_type_name: Optional[str] = None
    dataset_type_info: Optional[JSONB] = None

class DatasetTypeSearch(RESTAPIBase):
    dataset_type_name: Optional[str] = None
    dataset_type_info: Optional[JSONB] = None

class DatasetTypeOutput(RESTAPIBase):
    id: Optional[ID] = None
    dataset_type_name: Optional[str] = None
    dataset_type_info: Optional[JSONB] = None


# ---------------------------------
# Dataset Classes
# ---------------------------------

class DatasetInput(RESTAPIBase):
    dataset_name: str
    collection_date: Optional[datetime] = None
    dataset_info: Optional[JSONB] = {}
    dataset_type_id: Optional[ID] = 0
    experiment_name: Optional[str] = None

class DatasetUpdate(RESTAPIBase):
    dataset_name: Optional[str] = None
    collection_date: Optional[datetime] = None
    dataset_info: Optional[JSONB] = None
    dataset_type_id: Optional[ID] = None

class DatasetSearch(RESTAPIBase):
    dataset_name: Optional[str] = None
    collection_date: Optional[datetime] = None
    dataset_info: Optional[JSONB] = None
    dataset_type_id: Optional[ID] = None
    experiment_name: Optional[str] = None

class DatasetOutput(RESTAPIBase):
    id: Optional[ID] = None
    dataset_name: Optional[str] = None
    collection_date: Optional[datetime] = None
    dataset_info: Optional[JSONB] = None
    dataset_type_id: Optional[ID] = None


# ---------------------------------
# Model Classes
# ---------------------------------

class ModelInput(RESTAPIBase):
    model_name: str
    model_url: Optional[str] = None
    model_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class ModelUpdate(RESTAPIBase):
    model_name: Optional[str] = None
    model_url: Optional[str] = None
    model_info: Optional[JSONB] = None

class ModelSearch(RESTAPIBase):
    model_name: Optional[str] = None
    model_url: Optional[str] = None
    model_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None

class ModelOutput(RESTAPIBase):
    id: Optional[ID] = None
    model_name: Optional[str] = None
    model_url: Optional[str] = None
    model_info: Optional[JSONB] = None


# --------------------------------
# Model Run Classes
# --------------------------------

class ModelRunInput(RESTAPIBase):
    model_name: str
    model_run_info: Optional[JSONB] = {}

class ModelRunUpdate(RESTAPIBase):
    model_run_info: Optional[JSONB] = None

class ModelRunSearch(RESTAPIBase):
    model_name: Optional[str] = None
    model_run_info: Optional[JSONB] = None

class ModelRunOutput(RESTAPIBase):
    id: Optional[ID] = None
    model_name: Optional[str] = None
    model_run_info: Optional[JSONB] = None

# --------------------------------
# Plant Classes
# --------------------------------

# --------------------------------
# Line Classes
# --------------------------------

class LineInput(RESTAPIBase):
    line_name: str
    species: Optional[str] = None
    line_info: Optional[JSONB] = {}

class LineUpdate(RESTAPIBase):
    line_name: Optional[str] = None
    species: Optional[str] = None
    line_info: Optional[JSONB] = None

class LineOutput(RESTAPIBase):
    id: Optional[ID] = None
    line_name: Optional[str] = None
    species: Optional[str] = None
    line_info: Optional[JSONB] = None

# --------------------------------
# Accession Classes
# --------------------------------

class AccessionInput(RESTAPIBase):
    accession_name: str
    line_name: Optional[str] = None
    species: Optional[str] = None
    accession_info: Optional[JSONB] = {}
    population_name: Optional[str] = None

class AccessionUpdate(RESTAPIBase):
    accession_name: Optional[str] = None
    species: Optional[str] = None
    accession_info: Optional[JSONB] = None

class AccessionOutput(RESTAPIBase):
    id: Optional[ID] = None
    accession_name: Optional[str] = None
    line_id: Optional[ID] = None
    species: Optional[str] = None
    accession_info: Optional[JSONB] = None

# --------------------------------
# Germplasm Resolver Classes
# --------------------------------

class ResolveRequest(RESTAPIBase):
    names: List[str]
    experiment_id: Optional[ID] = None

class ResolveCandidateOutput(RESTAPIBase):
    id: str
    kind: str
    name: str
    score: float = 1.0

class ResolveResultOutput(RESTAPIBase):
    input_name: str
    match_kind: str
    accession_id: Optional[str] = None
    line_id: Optional[str] = None
    canonical_name: Optional[str] = None
    candidates: List[ResolveCandidateOutput] = []

class ResolveResponse(RESTAPIBase):
    results: List[ResolveResultOutput]

class AliasBulkEntry(RESTAPIBase):
    alias: str
    accession_name: Optional[str] = None
    line_name: Optional[str] = None
    source: Optional[str] = None

class AliasBulkRequest(RESTAPIBase):
    scope: str = "global"
    experiment_id: Optional[ID] = None
    entries: List[AliasBulkEntry]

class AliasBulkError(RESTAPIBase):
    index: int
    alias: str
    reason: str

class AliasBulkResponse(RESTAPIBase):
    created: int
    updated: int
    errors: List[AliasBulkError] = []


# --------------------------------
# Plot Classes
# --------------------------------

class PlotInput(RESTAPIBase):
    plot_number: int
    plot_row_number: int
    plot_column_number: int
    plot_info: Optional[JSONB] = {}
    plot_geometry_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    accession_name: Optional[str] = None
    population_name: Optional[str] = None

class PlotBulkInput(RESTAPIBase):
    plots: List[PlotInput]

class PlotBulkResponse(RESTAPIBase):
    submitted_count: int
    skipped_count: int

class PlotUpdate(RESTAPIBase):
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    plot_info: Optional[JSONB] = None
    plot_geometry_info: Optional[JSONB] = None

class PlotSearch(RESTAPIBase):
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    plot_info: Optional[JSONB] = None
    plot_geometry_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    accession_name: Optional[str] = None
    population_name: Optional[str] = None

class PlotOutput(RESTAPIBase):
    id: Optional[ID] = None
    experiment_id: Optional[ID] = None
    season_id: Optional[ID] = None
    site_id: Optional[ID] = None
    accession_id: Optional[ID] = None
    population_id: Optional[ID] = None
    plot_number: int = None
    plot_row_number: int = None
    plot_column_number: int = None
    plot_info: Optional[JSONB] = None
    plot_geometry_info: Optional[JSONB] = None


# --------------------------------
# Procedure Classes
# --------------------------------

class ProcedureInput(RESTAPIBase):
    procedure_name: str
    procedure_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class ProcedureUpdate(RESTAPIBase):
    procedure_info: Optional[JSONB] = None
    procedure_name: Optional[str] = None

class ProcedureSearch(RESTAPIBase):
    procedure_name: Optional[str] = None
    procedure_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None

class ProcedureOutput(RESTAPIBase):
    id: Optional[ID] = None
    procedure_name: str = None
    procedure_info: Optional[JSONB] = None


# --------------------------------
# Procedure Run Classes
# --------------------------------

class ProcedureRunInput(RESTAPIBase):
    procedure_name: str
    procedure_run_info: Optional[JSONB] = {}

class ProcedureRunUpdate(RESTAPIBase):
    procedure_run_info: Optional[JSONB] = None

class ProcedureRunSearch(RESTAPIBase):
    procedure_name: Optional[str] = None
    procedure_run_info: Optional[JSONB] = None

class ProcedureRunOutput(RESTAPIBase):
    id: Optional[ID] = None
    procedure_name: str = None
    procedure_run_info: Optional[JSONB] = None


# --------------------------------
# Script Classes
# --------------------------------

class ScriptInput(RESTAPIBase):
    script_name: str
    script_url: Optional[str] = None
    script_extension: Optional[str] = None
    script_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class ScriptUpdate(RESTAPIBase):
    script_name: Optional[str] = None
    script_url: Optional[str] = None
    script_extension: Optional[str] = None
    script_info: Optional[JSONB] = None

class ScriptSearch(RESTAPIBase):
    script_name: Optional[str] = None
    script_url: Optional[str] = None
    script_extension: Optional[str] = None
    script_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None

class ScriptOutput(RESTAPIBase):
    id: Optional[ID] = None
    script_name: str = None
    script_url: Optional[str] = None
    script_extension: Optional[str] = None
    script_info: Optional[JSONB] = None


# --------------------------------
# Script Run Classes
# --------------------------------

class ScriptRunInput(RESTAPIBase):
    script_name: str
    script_run_info: Optional[JSONB] = {}

class ScriptRunUpdate(RESTAPIBase):
    script_run_info: Optional[JSONB] = None

class ScriptRunSearch(RESTAPIBase):
    script_name: Optional[str] = None
    script_run_info: Optional[JSONB] = None

class ScriptRunOutput(RESTAPIBase):
    id: Optional[ID] = None
    script_name: str = None
    script_run_info: Optional[JSONB] = None

# --------------------------------
# Sensor Platform Classes
# --------------------------------

class SensorPlatformInput(RESTAPIBase):
    sensor_platform_name: str
    sensor_platform_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class SensorPlatformUpdate(RESTAPIBase):
    sensor_platform_name: Optional[str] = None
    sensor_platform_info: Optional[JSONB] = None

class SensorPlatformSearch(RESTAPIBase):
    sensor_platform_name: Optional[str] = None
    sensor_platform_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None

class SensorPlatformOutput(RESTAPIBase):
    id: Optional[ID] = None
    sensor_platform_name: str = None
    sensor_platform_info: Optional[JSONB] = None


# --------------------------------
# Sensor Type Classes
# --------------------------------

class SensorTypeInput(RESTAPIBase):
    sensor_type_name: str
    sensor_type_info: Optional[JSONB] = {}

class SensorTypeUpdate(RESTAPIBase):
    sensor_type_name: Optional[str] = None
    sensor_type_info: Optional[JSONB] = None

class SensorTypeSearch(RESTAPIBase):
    sensor_type_name: Optional[str] = None
    sensor_type_info: Optional[JSONB] = None

class SensorTypeOutput(RESTAPIBase):
    id: Optional[ID] = None
    sensor_type_name: str = None
    sensor_type_info: Optional[JSONB] = None

# --------------------------------
# Sensor Classes
# --------------------------------

class SensorInput(RESTAPIBase):
    sensor_name: str
    sensor_type_id: ID = 0
    sensor_data_type_id: ID = 0 
    sensor_data_format_id: ID = 0
    sensor_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None
    sensor_platform_name: Optional[str] = None

class SensorUpdate(RESTAPIBase):
    sensor_name: Optional[str] = None
    sensor_type_id: Optional[ID] = None
    sensor_data_type_id: Optional[ID] = None
    sensor_data_format_id: Optional[ID] = None
    sensor_info: Optional[JSONB] = None

class SensorSearch(RESTAPIBase):
    sensor_name: Optional[str] = None
    sensor_type_id: Optional[ID] = None
    sensor_data_type_id: Optional[ID] = None
    sensor_data_format_id: Optional[ID] = None
    sensor_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    sensor_platform_name: Optional[str] = None

class SensorOutput(RESTAPIBase):
    id: Optional[ID] = None
    sensor_name: str = None
    sensor_type_id: ID = None
    sensor_data_type_id: ID = None
    sensor_data_format_id: ID = None
    sensor_info: Optional[JSONB] = None

# --------------------------------
# Trait Level Classes
# --------------------------------

class TraitLevelInput(RESTAPIBase):
    trait_level_name: str
    trait_level_info: Optional[JSONB] = {}

class TraitLevelUpdate(RESTAPIBase):
    trait_level_name: Optional[str] = None
    trait_level_info: Optional[JSONB] = None

class TraitLevelSearch(RESTAPIBase):
    trait_level_name: Optional[str] = None
    trait_level_info: Optional[JSONB] = None

class TraitLevelOutput(RESTAPIBase):
    id: Optional[ID] = None
    trait_level_name: str = None
    trait_level_info: Optional[JSONB] = None


# --------------------------------
# Trait Classes
# --------------------------------

class TraitInput(RESTAPIBase):
    trait_name: str
    trait_units: Optional[str] = None
    trait_level_id: ID = 0
    trait_metrics: Optional[JSONB] = None
    trait_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class TraitUpdate(RESTAPIBase):
    trait_name: Optional[str] = None
    trait_units: Optional[str] = None
    trait_level_id: Optional[ID] = None
    trait_metrics: Optional[JSONB] = None
    trait_info: Optional[JSONB] = None

class TraitSearch(RESTAPIBase):
    trait_name: Optional[str] = None
    trait_units: Optional[str] = None
    trait_level_id: Optional[ID] = None
    trait_metrics: Optional[JSONB] = None
    trait_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None

class TraitOutput(RESTAPIBase):
    id: Optional[ID] = None
    trait_name: str = None
    trait_units: Optional[str] = None
    trait_level_id: ID = None
    trait_metrics: Optional[JSONB] = None
    trait_info: Optional[JSONB] = None


# --------------------------------
# Dataset Record Classes
# --------------------------------

class DatasetRecordInput(RESTAPIBase):
    timestamp: datetime
    dataset_data: Optional[JSONB] = {}
    collection_date: Optional[datetime] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    record_file: Optional[UploadFile] = None
    record_info: Optional[JSONB] = {}

class DatasetRecordSearch(RESTAPIBase):
    dataset_name: Optional[str] = None
    dataset_data: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    collection_date: Optional[datetime] = None
    record_info: Optional[JSONB] = None

class DatasetRecordFilter(RESTAPIBase):
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    dataset_names: Optional[List[str]] = None
    experiment_names: Optional[List[str]] = None
    season_names: Optional[List[str]] = None
    site_names: Optional[List[str]] = None

class DatasetRecordUpdate(RESTAPIBase):
    dataset_data: Optional[JSONB] = None
    record_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None

class DatasetRecordOutput(RESTAPIBase):
    id: Optional[ID] = None
    timestamp: datetime = None
    collection_date: Optional[datetime] = None
    dataset_id: ID = None
    dataset_name: str = None
    dataset_data: JSONB = None
    experiment_id: Optional[ID] = None
    experiment_name: Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    record_file: Optional[str] = None
    record_info: Optional[JSONB] = None


# --------------------------------
# Model Record Classes
# --------------------------------

class ModelRecordInput(RESTAPIBase):
    timestamp: datetime
    dataset_name: str
    model_data: JSONB
    collection_date: Optional[datetime] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    record_file: Optional[UploadFile] = None
    record_info: Optional[JSONB] = {}

class ModelRecordSearch(RESTAPIBase):
    model_name: Optional[str] = None
    model_data: Optional[JSONB] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    collection_date: Optional[datetime] = None
    record_info: Optional[JSONB] = None

class ModelRecordFilter(RESTAPIBase):
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    model_names: Optional[List[str]] = None
    dataset_names: Optional[List[str]] = None
    experiment_names: Optional[List[str]] = None
    season_names: Optional[List[str]] = None
    site_names: Optional[List[str]] = None

class ModelRecordUpdate(RESTAPIBase):
    model_data: Optional[JSONB] = None
    record_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None


class ModelRecordOutput(RESTAPIBase):
    id: Optional[ID] = None
    timestamp: datetime = None
    collection_date: Optional[datetime] = None
    dataset_id: ID = None
    dataset_name: str = None
    model_id: ID = None
    model_name: str = None
    model_data: JSONB = None
    experiment_id: Optional[ID] = None
    experiment_name: Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    record_file: Optional[str] = None
    record_info: Optional[JSONB] = None


# --------------------------------
# Procedure Record Classes
# --------------------------------

class ProcedureRecordInput(RESTAPIBase):
    timestamp: datetime
    dataset_name: str 
    procedure_data: JSONB
    collection_date: Optional[datetime] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    record_file: Optional[UploadFile] = None
    record_info: Optional[JSONB] = {}

class ProcedureRecordSearch(RESTAPIBase):
    procedure_name: Optional[str] = None
    procedure_data: Optional[JSONB] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    collection_date: Optional[datetime] = None
    record_info: Optional[JSONB] = None

class ProcedureRecordFilter(RESTAPIBase):
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    procedure_names: Optional[List[str]] = None
    dataset_names: Optional[List[str]] = None
    experiment_names: Optional[List[str]] = None
    season_names: Optional[List[str]] = None
    site_names: Optional[List[str]] = None

class ProcedureRecordUpdate(RESTAPIBase):
    procedure_data: Optional[JSONB] = None
    record_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None

class ProcedureRecordOutput(RESTAPIBase):
    id: Optional[ID] = None
    timestamp: datetime = None
    collection_date: Optional[datetime] = None
    dataset_id: ID = None
    dataset_name: str = None
    procedure_id: ID = None
    procedure_name: str = None
    procedure_data: JSONB = None
    experiment_id: Optional[ID] = None
    experiment_name: Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    record_file: Optional[str] = None
    record_info: Optional[JSONB] = None

# --------------------------------
# Script Record Classes
# --------------------------------

class ScriptRecordInput(RESTAPIBase):
    timestamp: datetime
    dataset_name: str
    script_data: JSONB
    collection_date: Optional[datetime] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    record_file: Optional[UploadFile] = None
    record_info: Optional[JSONB] = {}

class ScriptRecordSearch(RESTAPIBase):
    script_name: Optional[str] = None
    script_data: Optional[JSONB] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    collection_date: Optional[datetime] = None
    record_info: Optional[JSONB] = None

class ScriptRecordFilter(RESTAPIBase):
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    script_names: Optional[List[str]] = None
    dataset_names: Optional[List[str]] = None
    experiment_names: Optional[List[str]] = None
    season_names: Optional[List[str]] = None
    site_names: Optional[List[str]] = None

class ScriptRecordUpdate(RESTAPIBase):
    script_data: Optional[JSONB] = None
    record_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None

class ScriptRecordOutput(RESTAPIBase):
    id: Optional[ID] = None
    timestamp: datetime = None
    collection_date: Optional[datetime] = None
    dataset_id: ID = None
    dataset_name: str = None
    script_id: ID = None
    script_name: str = None
    script_data: JSONB = None
    experiment_id: Optional[ID] = None
    experiment_name: Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    record_file: Optional[str] = None
    record_info: Optional[JSONB] = None


# --------------------------------
# Sensor Record Classes
# --------------------------------

class SensorRecordInput(RESTAPIBase):
    timestamp: datetime
    sensor_data: JSONB
    collection_date: Optional[datetime] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    record_file: Optional[UploadFile] = None
    record_info: Optional[JSONB] = {}

class SensorRecordSearch(RESTAPIBase):
    sensor_name: Optional[str] = None
    sensor_data: Optional[JSONB] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    collection_date: Optional[datetime] = None
    record_info: Optional[JSONB] = None

class SensorRecordFilter(RESTAPIBase):
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    sensor_names: Optional[List[str]] = None
    dataset_names: Optional[List[str]] = None
    experiment_names: Optional[List[str]] = None
    season_names: Optional[List[str]] = None
    site_names: Optional[List[str]] = None

class SensorRecordUpdate(RESTAPIBase):
    sensor_data: Optional[JSONB] = None
    record_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None

class SensorRecordOutput(RESTAPIBase):
    id: Optional[ID] = None
    timestamp: datetime = None
    collection_date: Optional[datetime] = None
    sensor_id: ID = None
    sensor_name: str = None
    sensor_data: JSONB = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    experiment_id: Optional[ID] = None
    experiment_name: Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    plot_id: Optional[ID] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    record_file: Optional[str] = None
    record_info: Optional[JSONB] = None


# --------------------------------
# Trait Record Classes
# --------------------------------

class TraitRecordInput(RESTAPIBase):
    timestamp: datetime
    trait_value: float
    collection_date: Optional[datetime] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    record_info: Optional[JSONB] = {}

class TraitRecordSearch(RESTAPIBase):
    trait_name: Optional[str] = None
    trait_value: Optional[float] = None
    dataset_name: Optional[str] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    collection_date: Optional[datetime] = None
    record_info: Optional[JSONB] = None

class TraitRecordFilter(RESTAPIBase):
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    trait_names: Optional[List[str]] = None
    dataset_names: Optional[List[str]] = None
    experiment_names: Optional[List[str]] = None
    season_names: Optional[List[str]] = None
    site_names: Optional[List[str]] = None

class TraitRecordUpdate(RESTAPIBase):
    trait_value: Optional[float] = None
    record_info: Optional[JSONB] = None
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None

class TraitRecordOutput(RESTAPIBase):
    id: Optional[ID] = None
    timestamp: datetime = None
    collection_date: Optional[datetime] = None
    trait_id: ID = None
    trait_name: str = None
    trait_value: float = None
    dataset_id: Optional[ID] = None
    dataset_name: Optional[str] = None
    experiment_id: Optional[ID] = None
    experiment_name: Optional[str] = None
    season_id: Optional[ID] = None
    season_name: Optional[str] = None
    site_id: Optional[ID] = None
    site_name: Optional[str] = None
    plot_id: Optional[ID] = None
    plot_number: Optional[int] = None
    plot_row_number: Optional[int] = None
    plot_column_number: Optional[int] = None
    record_info: Optional[JSONB] = None


class TraitRecordBulkInput(RESTAPIBase):
    records: List[dict]
    experiment_name: Optional[str] = None
    season_name: Optional[str] = None
    site_name: Optional[str] = None
    dataset_name: Optional[str] = None
    collection_date: Optional[datetime] = None

class TraitRecordBulkOutput(RESTAPIBase):
    inserted_count: int
    record_ids: List[str]


# --------------------------------
# Job Classes
# --------------------------------

class JobSubmitInput(RESTAPIBase):
    job_type: str
    parameters: Optional[JSONB] = {}
    experiment_id: Optional[ID] = None

class JobOutput(RESTAPIBase):
    id: Optional[ID] = None
    job_type: str
    status: str = "PENDING"
    progress: float = 0.0
    progress_detail: Optional[dict] = None
    parameters: Optional[dict] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    experiment_id: Optional[ID] = None
    worker_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class JobProgressUpdate(RESTAPIBase):
    progress: float
    progress_detail: Optional[JSONB] = None

class JobClaimInput(RESTAPIBase):
    job_type: str
    worker_id: str

class JobStatusUpdate(RESTAPIBase):
    status: str
    worker_id: Optional[str] = None
    progress: Optional[float] = None
    progress_detail: Optional[JSONB] = None
    result: Optional[JSONB] = None
    error_message: Optional[str] = None


# --------------------------------
# Variant Classes
# --------------------------------
class VariantInput(RESTAPIBase):
    variant_name: str
    chromosome: int
    position: float
    alleles: str
    design_sequence: Optional[str] = ''
    variant_info: Optional[JSONB] = {}

class VariantBulkInput(RESTAPIBase):
    variants: List[dict]

class VariantUpdate(RESTAPIBase):
    variant_name: Optional[str] = None
    chromosome: Optional[int] = None
    position: Optional[float] = None
    alleles: Optional[str] = None
    design_sequence: Optional[str] = None
    variant_info: Optional[JSONB] = None

class VariantOutput(RESTAPIBase):
    id: Optional[ID] = None
    variant_name: Optional[str] = None
    chromosome: Optional[int] = None
    position: Optional[float] = None
    alleles: Optional[str] = None
    design_sequence: Optional[str] = None
    variant_info: Optional[JSONB] = None


# --------------------------------
# Genotype Classes
# --------------------------------
class GenotypingStudyInput(RESTAPIBase):
    study_name: str
    study_info: Optional[JSONB] = {}
    experiment_name: Optional[str] = None

class GenotypingStudyUpdate(RESTAPIBase):
    study_name: Optional[str] = None
    study_info: Optional[JSONB] = None

class GenotypingStudyOutput(RESTAPIBase):
    id: Optional[ID] = None
    study_name: Optional[str] = None
    study_info: Optional[JSONB] = None


# --------------------------------
# Genotype Record Classes
# --------------------------------
class GenotypeRecordInput(RESTAPIBase):
    study_id: Optional[ID] = None
    study_name: Optional[str] = None
    variant_id: Optional[ID] = None
    variant_name: Optional[str] = None
    chromosome: Optional[int] = None
    position: Optional[float] = None
    accession_id: Optional[ID] = None
    accession_name: Optional[str] = None
    call_value: str
    record_info: Optional[JSONB] = {}

class GenotypeRecordBulkInput(RESTAPIBase):
    records: List[dict]


class GenotypeMatrixVariantRow(RESTAPIBase):
    variant_name: str
    chromosome: Optional[int] = None
    position: Optional[float] = None
    alleles: Optional[str] = None
    design_sequence: Optional[str] = None
    calls: List[Optional[str]]


class GenotypeMatrixBatchInput(RESTAPIBase):
    sample_headers: List[str]
    variant_rows: List[GenotypeMatrixVariantRow]
    record_info: Optional[JSONB] = None


class GenotypeMatrixBatchResult(RESTAPIBase):
    variants_inserted: int
    records_inserted: int
    errors: List[str] = []


class GenotypeRecordOutput(RESTAPIBase):
    id: Optional[ID] = None
    study_id: Optional[ID] = None
    study_name: Optional[str] = None
    variant_id: Optional[ID] = None
    variant_name: Optional[str] = None
    chromosome: Optional[int] = None
    position: Optional[float] = None
    accession_id: Optional[ID] = None
    accession_name: Optional[str] = None
    call_value: Optional[str] = None
    record_info: Optional[JSONB] = None
