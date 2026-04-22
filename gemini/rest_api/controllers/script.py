from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller
from litestar.response import Stream, Redirect
from litestar.serialization import encode_json
from litestar.enums import RequestEncodingType

from collections.abc import AsyncGenerator, Generator

from pydantic import BaseModel

from gemini.api.script import Script
from gemini.api.script_record import ScriptRecord
from gemini.rest_api.models import ( 
    ScriptInput, 
    ScriptOutput, 
    ScriptUpdate,
    ScriptRunOutput,
    DatasetOutput,
    ExperimentOutput, 
    RESTAPIError, 
    JSONB, 
    str_to_dict
)

from gemini.rest_api.models import (
    ScriptRecordInput,
    ScriptRecordOutput,
    ScriptRecordUpdate,
)

from gemini.rest_api.file_handler import api_file_handler

from typing import List, Annotated, Optional

async def script_records_bytes_generator(script_record_generator: Generator[ScriptRecord, None, None]) -> AsyncGenerator[bytes, None]:
    for record in script_record_generator:
        record = record.model_dump(exclude_none=True)
        record = encode_json(record) + b'\n'
        yield record


class ScriptScriptRunInput(BaseModel):
    script_run_info: Optional[JSONB] = {}

class ScriptDatasetInput(BaseModel):
    dataset_name: str
    dataset_info: Optional[JSONB] = {}
    collection_date: Optional[str] = None
    experiment_name: Optional[str] = 'Experiment A'



class ScriptController(Controller):

    # Get All Scripts
    @get(path="/all", sync_to_thread=True)
    def get_all_scripts(self, limit: int = 100, offset: int = 0) -> List[ScriptOutput]:
        try:
            scripts = Script.get_all(limit=limit, offset=offset)
            return scripts or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all scripts"
            )
            return Response(content=error, status_code=500)

    # Get Scripts
    @get(sync_to_thread=True)
    def get_scripts(
        self,
        script_name: Optional[str] = None,
        script_url: Optional[str] = None,
        script_extension: Optional[str] = None,
        script_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = 'Experiment A'
    ) -> List[ScriptOutput]:
        try:
            if script_info is not None:
                script_info = str_to_dict(script_info)

            scripts = Script.search(
                script_name=script_name,
                script_url=script_url,
                script_extension=script_extension,
                script_info=script_info,
                experiment_name=experiment_name
            )
            return scripts or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving scripts"
            )
            return Response(content=error, status_code=500)
        
    # Get Script by ID
    @get(path="/id/{script_id:str}", sync_to_thread=True)
    def get_script_by_id(
        self, script_id: str
    ) -> ScriptOutput:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return script
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the script"
            )
            return Response(content=error, status_code=500)
        

    # Create Script
    @post(sync_to_thread=True)
    def create_script(
        self,
        data: Annotated[ScriptInput, Body]
    ) -> ScriptOutput:
        try:
            script = Script.create(
                script_name=data.script_name,
                script_url=data.script_url,
                script_extension=data.script_extension,
                script_info=data.script_info,
                experiment_name=data.experiment_name
            )
            if script is None:
                error = RESTAPIError(
                    error="Script not created",
                    error_description="The script was not created"
                )
                return Response(content=error, status_code=500)
            return script
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the script"
            )
            return Response(content=error, status_code=500)
        
    # Update Script
    @patch(path="/id/{script_id:str}", sync_to_thread=True)
    def update_script(
        self,
        script_id: str,
        data: Annotated[ScriptUpdate, Body]
    ) -> ScriptOutput:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            script = script.update(
                script_name=data.script_name,
                script_url=data.script_url,
                script_extension=data.script_extension,
                script_info=data.script_info
            )
            if script is None:
                error = RESTAPIError(
                    error="Script not updated",
                    error_description="The script was not updated"
                )
                return Response(content=error, status_code=500)
            return script
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the script"
            )
            return Response(content=error, status_code=500)
        
    # Delete Script
    @delete(path="/id/{script_id:str}", sync_to_thread=True)
    def delete_script(
        self,
        script_id: str
    ) -> None:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = script.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Script not deleted",
                    error_description="The script was not deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the script"
            )
            return Response(content=error, status_code=500)
        
    # Get Associated Experiments
    @get(path="/id/{script_id:str}/experiments", sync_to_thread=True)
    def get_script_experiments(
        self, script_id: str
    ) -> List[ExperimentOutput]:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return script.get_associated_experiments() or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated experiments"
            )
            return Response(content=error, status_code=500)

        
    # Get Script Runs
    @get(path="/id/{script_id:str}/runs", sync_to_thread=True)
    def get_script_runs(
        self, script_id: str
    ) -> List[ScriptRunOutput]:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return script.get_associated_runs() or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving script runs"
            )
            return Response(content=error, status_code=500)
        
    # Get Script Datasets
    @get(path="/id/{script_id:str}/datasets", sync_to_thread=True)
    def get_script_datasets(
        self, script_id: str
    ) -> List[DatasetOutput]:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return script.get_associated_datasets() or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving datasets"
            )
            return Response(content=error, status_code=500)
        
    # Create Script Run
    @post(path="/id/{script_id:str}/runs", sync_to_thread=True)
    def create_script_run(
        self,
        script_id: str,
        data: Annotated[ScriptScriptRunInput, Body]
    ) -> ScriptRunOutput:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            script_run = script.create_new_run(script_run_info=data.script_run_info)
            if script_run is None:
                error = RESTAPIError(
                    error="Script run not created",
                    error_description="The script run was not created"
                )
                return Response(content=error, status_code=500)
            return script_run
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the script run"
            )
            return Response(content=error, status_code=500)
        
    # Create Script Dataset
    @post(path="/id/{script_id:str}/datasets", sync_to_thread=True)
    def create_script_dataset(
        self,
        script_id: str,
        data: Annotated[ScriptDatasetInput, Body]
    ) -> DatasetOutput:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            dataset = script.create_new_dataset(
                dataset_name=data.dataset_name,
                dataset_info=data.dataset_info,
                collection_date=data.collection_date,
                experiment_name=data.experiment_name
            )
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not created",
                    error_description="The dataset was not created"
                )
                return Response(content=error, status_code=500)
            return dataset
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the dataset"
            )
            return Response(content=error, status_code=500)
    

    # Add a Script Record
    @post(path="/id/{script_id:str}/records")
    async def add_script_record(
        self,
        script_id: str,
        data: Annotated[ScriptRecordInput, Body(media_type=RequestEncodingType.MULTI_PART)]
    ) -> ScriptRecordOutput:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            
            record_file_path = None
            if data.record_file:
                record_file_path = await api_file_handler.create_file(data.record_file)

            add_success, inserted_record_ids = script.insert_record(
                timestamp=data.timestamp,
                collection_date=data.collection_date,
                script_data=data.script_data,
                dataset_name=data.dataset_name,
                experiment_name=data.experiment_name,
                season_name=data.season_name,
                site_name=data.site_name,
                record_file=record_file_path,
                record_info=data.record_info
            )
            if not add_success or not inserted_record_ids:
                error = RESTAPIError(
                    error="Script record not added",
                    error_description="The script record was not added"
                )
                return Response(content=error, status_code=500)
            inserted_record_id = inserted_record_ids[0]
            inserted_script_record = ScriptRecord.get_by_id(id=inserted_record_id)
            if inserted_script_record is None:
                error = RESTAPIError(
                    error="Script record not found",
                    error_description="The script record with the given ID was not found after insertion"
                )
                return Response(content=error, status_code=404)
            return inserted_script_record
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while adding the script record"
            )
            return Response(content=error, status_code=500) 

    # Search Script Records
    @get(path="/id/{script_id:str}/records", sync_to_thread=True)
    def search_script_records(
        self,
        script_id: str,
        experiment_name: Optional[str] = None,
        season_name: Optional[str] = None,
        site_name: Optional[str] = None,
        collection_date: Optional[str] = None
    ) -> Stream:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            script_records = script.search_records(
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                collection_date=collection_date
            )
            return Stream(script_records_bytes_generator(script_records), media_type="application/ndjson")
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving script records"
            )
            return Response(content=error, status_code=500)
        
        
    @get(path="/id/{script_id:str}/records/filter", sync_to_thread=True)
    def filter_script_records(
        self,
        script_id: str,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> Stream:
        try:
            script = Script.get_by_id(id=script_id)
            if script is None:
                error = RESTAPIError(
                    error="Script not found",
                    error_description="The script with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            script_records = script.filter_records(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return Stream(script_records_bytes_generator(script_records), media_type="application/ndjson")
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while filtering script records"
            )
            return Response(content=error, status_code=500)

        
    # Get Script Record by ID
    @get(path="/records/id/{record_id:str}", sync_to_thread=True)
    def get_script_record_by_id(
        self,
        record_id: str
    ) -> ScriptRecordOutput:
        try:
            script_record = ScriptRecord.get_by_id(id=record_id)
            if script_record is None:
                error = RESTAPIError(
                    error="Script record not found",
                    error_description="The script record with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return script_record
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the script record"
            )
            return Response(content=error, status_code=500)
        
    # Get Script Record File
    @get(path="/records/id/{record_id:str}/download", sync_to_thread=True)
    def download_script_record_file(
        self,
        record_id: str
    ) -> Redirect:
        try:
            script_record = ScriptRecord.get_by_id(id=record_id)
            if script_record is None:
                error = RESTAPIError(
                    error="Script record not found",
                    error_description="The script record with the given ID was not found"
                )
                return Response(content=error, status_code=404) # This will be a type error at runtime
            record_file = script_record.record_file
            if record_file is None:
                error = RESTAPIError(
                    error="Script record file not found",
                    error_description="The script record file with the given ID was not found"
                )
                return Response(content=error, status_code=404) # This will be a type error at runtime
            bucket_name = "gemini"
            object_name = record_file
            object_path = f"{bucket_name}/{object_name}"
            return Redirect(path=f"/api/files/download/{object_path}")
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the script record file"
            )
            return Response(content=error, status_code=500)
        
    # Update Script Record
    @patch(path="/records/id/{record_id:str}", sync_to_thread=True)
    def update_script_record(
        self,
        record_id: str,
        data: Annotated[ScriptRecordUpdate, Body]
    ) -> ScriptRecordOutput:
        try:
            script_record = ScriptRecord.get_by_id(id=record_id)
            if script_record is None:
                error = RESTAPIError(
                    error="Script record not found",
                    error_description="The script record with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            script_record = script_record.update(
                script_data=data.script_data,
                record_info=data.record_info
            )
            if script_record is None:
                error = RESTAPIError(
                    error="Script record not updated",
                    error_description="The script record was not updated"
                )
                return Response(content=error, status_code=500)
            return script_record
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the script record"
            )
            return Response(content=error, status_code=500)
        

    # Delete Script Record
    @delete(path="/records/id/{record_id:str}", sync_to_thread=True)
    def delete_script_record(
        self,
        record_id: str
    ) -> None:
        try:
            script_record = ScriptRecord.get_by_id(id=record_id)
            if script_record is None:
                error = RESTAPIError(
                    error="Script record not found",
                    error_description="The script record with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = script_record.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Script record not deleted",
                    error_description="The script record was not deleted"
                )
                return Response(content=error, status_code=500)
            return None # Indicates success with 204 No Content if nothing is returned
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the script record"
            )
            return Response(content=error, status_code=500)