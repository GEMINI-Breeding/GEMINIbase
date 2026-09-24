from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller
from litestar.response import Stream, Redirect
from litestar.serialization import encode_json
from litestar.enums import RequestEncodingType


from collections.abc import AsyncGenerator, Generator

from gemini.api.dataset import Dataset
from gemini.api.dataset_record import DatasetRecord
from gemini.api.enums import GEMINIDatasetType
from gemini.rest_api.models import (
    DatasetInput,
    DatasetOutput,
    RESTAPIError,
    DatasetUpdate,
    ExperimentOutput,
    TraitOutput,
    str_to_dict,
    JSONB
)
from gemini.rest_api.models import (
    DatasetRecordInput,
    DatasetRecordOutput,
    DatasetRecordUpdate,
)

from gemini.rest_api.file_handler import api_file_handler
from gemini.rest_api.ndjson import ndjson_stream

from typing import List, Annotated, Optional


class DatasetController(Controller):

    # Get All Datasets
    @get(path="/all", sync_to_thread=True)
    def get_all_datasets(self, limit: int = 100, offset: int = 0) -> List[DatasetOutput]:
        try:
            datasets = Dataset.get_all(limit=limit, offset=offset)
            return datasets or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all datasets"
            )
            return Response(content=error, status_code=500)

    # Get Datasets
    @get(sync_to_thread=True)
    def get_datasets(
        self,
        dataset_name: Optional[str] = None,
        dataset_info: Optional[JSONB] = None,
        dataset_type_id: Optional[int] = None,
        experiment_name: Optional[str] = 'Experiment A',
        collection_date: Optional[str] = None
    ) -> List[DatasetOutput]:
        try:
            if dataset_info is not None:
                dataset_info = str_to_dict(dataset_info)

            datasets = Dataset.search(
                dataset_name=dataset_name,
                dataset_info=dataset_info,
                dataset_type=GEMINIDatasetType(dataset_type_id) if dataset_type_id else None,
                experiment_name=experiment_name,
                collection_date=collection_date
            )
            return datasets or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving datasets"
            )
            return Response(content=error, status_code=500)
        
    # Get Dataset by ID
    @get(path="/id/{dataset_id:str}", sync_to_thread=True)
    def get_dataset_by_id(
        self, dataset_id: str
    ) -> DatasetOutput:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            return dataset
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the dataset"
            )
            return Response(content=error, status_code=500)
        
    # Create Dataset
    @post(sync_to_thread=True)
    def create_dataset(
        self, data: Annotated[DatasetInput, Body]
    ) -> DatasetOutput:
        try:
            dataset = Dataset.create(
                collection_date=data.collection_date,
                dataset_name=data.dataset_name,
                dataset_info=data.dataset_info,
                dataset_type=GEMINIDatasetType(data.dataset_type_id),
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
        
    # Update Dataset
    @patch(path="/id/{dataset_id:str}", sync_to_thread=True)
    def update_dataset(
        self, dataset_id: str, data: Annotated[DatasetUpdate, Body]
    ) -> DatasetOutput:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            
            dataset = dataset.update(
                collection_date=data.collection_date,
                dataset_name=data.dataset_name,
                dataset_info=data.dataset_info,
                dataset_type=GEMINIDatasetType(data.dataset_type_id) if data.dataset_type_id else None,
            )
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not updated",
                    error_description="The dataset could not be updated"
                )
                return Response(content=error, status_code=500)
            return dataset
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the dataset"
            )
            return Response(content=error, status_code=500)
        
    # Delete Dataset
    @delete(path="/id/{dataset_id:str}", sync_to_thread=True)
    def delete_dataset(
        self, dataset_id: str
    ) -> None:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            is_deleted = dataset.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Dataset not deleted",
                    error_description="The dataset could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the dataset"
            )
            return Response(content=error, status_code=500)
        
    # Get Associated Traits
    @get(path="/id/{dataset_id:str}/traits", sync_to_thread=True)
    def get_associated_traits(
        self, dataset_id: str
    ) -> List[TraitOutput]:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            return dataset.get_associated_traits() or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated traits"
            )
            return Response(content=error, status_code=500)

    # Get Associated Experiments
    @get(path="/id/{dataset_id:str}/experiments", sync_to_thread=True)
    def get_associated_experiments(
        self, dataset_id: str
    ) -> List[ExperimentOutput]:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            return dataset.get_associated_experiments() or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated experiments"
            )
            return Response(content=error, status_code=500)
        
    # Count of `experiment_files` rows tied to this dataset.
    # Used by the Manage Data UI to show a "(N files)" hint next to
    # each dataset row without paying the cost of fetching the full
    # listing. Trait/sensor/etc. record files that live in the
    # columnar `*_records` tables are not counted here — those use
    # the legacy `dataset_data/` prefix and aren't tracked in
    # experiment_files.
    @get(path="/id/{dataset_id:str}/file_count", sync_to_thread=True)
    def get_dataset_file_count(
        self, dataset_id: str
    ) -> dict:
        try:
            from gemini.db.core.base import db_engine
            from gemini.db.models.experiment_files import ExperimentFileModel
            from sqlalchemy import func, select

            with db_engine.get_session() as session:
                count = session.execute(
                    select(func.count())
                    .select_from(ExperimentFileModel)
                    .where(ExperimentFileModel.dataset_id == dataset_id)
                ).scalar_one()
            return {"dataset_id": dataset_id, "file_count": int(count or 0)}
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while counting dataset files"
            )
            return Response(content=error, status_code=500)

    # Add a Dataset Record
    @post(path="/id/{dataset_id:str}/records", sync_to_thread=True)
    def add_dataset_record(
        self,
        dataset_id: str,
        data: Annotated[DatasetRecordInput, Body(media_type=RequestEncodingType.MULTI_PART)]
    ) -> DatasetRecordOutput:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            
            with api_file_handler.saved_upload(data.record_file) as record_file_path:
                add_success, inserted_record_ids = dataset.insert_record(
                    timestamp=data.timestamp,
                    collection_date=data.collection_date,
                    dataset_data=data.dataset_data,
                    experiment_name=data.experiment_name,
                    season_name=data.season_name,
                    site_name=data.site_name,
                    record_file=record_file_path,
                    record_info=data.record_info
                )
            if not add_success:
                error = RESTAPIError(
                    error="Dataset record not added",
                    error_description="The dataset record was not added"
                )
                return Response(content=error, status_code=500)
            inserted_record_id = inserted_record_ids[0]
            inserted_dataset_record = DatasetRecord.get_by_id(id=inserted_record_id)
            if inserted_dataset_record is None:
                error = RESTAPIError(
                    error="Dataset record not found",
                    error_description="The dataset record was not found"
                )
                return Response(content=error, status_code=404)
            return inserted_dataset_record
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while adding the dataset record"
            )
            return Response(content=error, status_code=500)


    # Search Dataset Records
    @get(path="/id/{dataset_id:str}/records", sync_to_thread=True)
    def search_dataset_records(
        self,
        dataset_id: str,
        experiment_name: Optional[str] = None,
        season_name: Optional[str] = None,
        site_name: Optional[str] = None,
        collection_date: Optional[str] = None
    ) -> Stream:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            records = dataset.search_records(
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                collection_date=collection_date
            )
            return ndjson_stream(records)
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving dataset records"
            )
            return Response(content=error, status_code=500)
        

    # Filter Dataset Records
    @get(path="/id/{dataset_id:str}/records/filter", sync_to_thread=True)
    def filter_dataset_records(
        self,
        dataset_id: str,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> Stream:
        try:
            dataset = Dataset.get_by_id(id=dataset_id)
            if dataset is None:
                error = RESTAPIError(
                    error="Dataset not found",
                    error_description="No dataset was found with the given ID"
                )
                return Response(content=error, status_code=404)
            records = dataset.filter_records(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return ndjson_stream(records)
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while filtering dataset records"
            )
            return Response(content=error, status_code=500)
    

    # Get Dataset Record by ID
    @get(path="/records/id/{record_id:str}", sync_to_thread=True)
    def get_dataset_record_by_id(
        self, record_id: str
    ) -> DatasetRecordOutput:
        try:
            dataset_record = DatasetRecord.get_by_id(id=record_id)
            if dataset_record is None:
                error = RESTAPIError(
                    error="Dataset record not found",
                    error_description="No dataset record was found with the given ID"
                )
                return Response(content=error, status_code=404)
            return dataset_record
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the dataset record"
            )
            return Response(content=error, status_code=500)
        
        
    # Download Dataset Record File
    @get(path="/records/id/{record_id:str}/download", sync_to_thread=True)
    def download_dataset_record_file(
        self, record_id: str
    ) -> Redirect:
        try:
            dataset_record = DatasetRecord.get_by_id(id=record_id)
            if dataset_record is None:
                error = RESTAPIError(
                    error="Dataset record not found",
                    error_description="No dataset record was found with the given ID"
                )
                return Response(content=error, status_code=404)
            record_file = dataset_record.record_file
            if record_file is None:
                error_html = RESTAPIError(
                    error="Dataset record file not found",
                    error_description="No dataset record file was found with the given ID"
                ).to_html()
                return Response(content=error_html, status_code=404)
            bucket_name = "gemini"
            object_name = record_file
            object_path = f"{bucket_name}/{object_name}"
            return Redirect(path=f"/api/files/download/{object_path}")
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the dataset record file"
            )
            return Response(content=error, status_code=500)

    # Update Dataset Record
    @patch(path="/records/id/{record_id:str}", sync_to_thread=True)
    def update_dataset_record(
        self, record_id: str, data: Annotated[DatasetRecordUpdate, Body]
    ) -> DatasetRecordOutput:
        try:
            dataset_record = DatasetRecord.get_by_id(id=record_id)
            if dataset_record is None:
                error = RESTAPIError(
                    error="Dataset record not found",
                    error_description="No dataset record was found with the given ID"
                )
                return Response(content=error, status_code=404)
            dataset_record = dataset_record.update(
                dataset_data=data.dataset_data,
                record_info=data.record_info,
            )
            if dataset_record is None:
                error = RESTAPIError(
                    error="Dataset record not updated",
                    error_description="The dataset record could not be updated"
                )
                return Response(content=error, status_code=500)
            return dataset_record
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the dataset record"
            )
            return Response(content=error, status_code=500)

    # Delete Dataset Record
    @delete(path="/records/id/{record_id:str}", sync_to_thread=True)
    def delete_dataset_record(
        self, record_id: str
    ) -> None:
        try:
            dataset_record = DatasetRecord.get_by_id(id=record_id)
            if dataset_record is None:
                error = RESTAPIError(
                    error="Dataset record not found",
                    error_description="No dataset record was found with the given ID"
                )
                return Response(content=error, status_code=404)
            is_deleted = dataset_record.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Dataset record not deleted",
                    error_description="The dataset record could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the dataset record"
            )
            return Response(content=error, status_code=500)

    @get(path="/id/{dataset_id:str}/location", sync_to_thread=True)
    def upload_location(self, dataset_id: str) -> dict:
        """Where an upload's files are: its folder and the scope that folder
        encodes (season, site, …) — what "Edit metadata" starts from."""
        from sqlalchemy import select

        from gemini.db.core.base import db_engine
        from gemini.db.models.experiment_files import ExperimentFileModel
        from gemini.rest_api import dataset_move as dm

        with db_engine.get_session() as session:
            names = session.execute(
                select(ExperimentFileModel.object_name).where(
                    ExperimentFileModel.dataset_id == dataset_id
                )
            ).scalars().all()
        try:
            folder = dm.source_folder(list(names), {})
        except dm.MoveError as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="No movable folder"),
                status_code=e.status if e.status != 400 else 422,
            )
        return {"folder": folder, "scope": dm.scope_of(folder)}

    @post(path="/id/{dataset_id:str}/move", sync_to_thread=True)
    def move_upload(self, dataset_id: str, data: dict) -> dict:
        """Edit an upload's season / site / population / date / platform /
        sensor — which, here, is its storage path — by moving its folder.
        See gemini/rest_api/dataset_move.py for the rules (no overwrite,
        rows follow the files, resumable, Processed/ outputs left in place).

        Body: {season, site, population, date, platform, sensor}
        Replaces the Flask-era update_metadata, which built paths without
        Raw/, moved every upload in a scope, overwrote, and left the file
        rows pointing at deleted objects.
        """
        from datetime import date as _date

        from minio.commonconfig import CopySource
        from sqlalchemy import select, update

        from gemini.db.core.base import db_engine
        from gemini.db.models.datasets import DatasetModel
        from gemini.db.models.experiment_files import ExperimentFileModel
        from gemini.rest_api import dataset_move as dm
        from gemini.rest_api.controllers.files import (
            minio_storage_config,
            minio_storage_provider,
        )

        bucket = minio_storage_config.bucket_name
        to = {f: str(data.get(f) or "") for f in dm.FIELDS}
        try:
            with db_engine.get_session() as session:
                names = session.execute(
                    select(ExperimentFileModel.object_name).where(
                        ExperimentFileModel.dataset_id == dataset_id,
                        ExperimentFileModel.bucket == bucket,
                    )
                ).scalars().all()
            folder = dm.source_folder(list(names), to)
            dm.ensure_entities(dm.scope_of(folder)["experiment"], to)

            def repoint(old: str, new: str) -> None:
                with db_engine.get_session() as session:
                    session.execute(
                        update(ExperimentFileModel)
                        .where(ExperimentFileModel.bucket == bucket,
                               ExperimentFileModel.object_name == old)
                        .values(object_name=new)
                    )
                    session.commit()

            client = minio_storage_provider.client
            result = dm.move_upload(
                folder=folder,
                to=to,
                list_objects=lambda p: minio_storage_provider.list_files(
                    prefix=p, recursive=True, bucket_name=bucket),
                exists=lambda o: minio_storage_provider.file_exists(
                    object_name=o, bucket_name=bucket),
                copy=lambda a, b: client.copy_object(bucket, b, CopySource(bucket, a)),
                remove=lambda o: client.remove_object(bucket, o),
                repoint=repoint,
            )
            try:
                new_date = _date.fromisoformat(to["date"])
                with db_engine.get_session() as session:
                    session.execute(
                        update(DatasetModel)
                        .where(DatasetModel.id == dataset_id)
                        .values(collection_date=new_date)
                    )
                    session.commit()
            except ValueError:
                pass  # a date folder that isn't ISO: leave the record's date
            return {
                "source": result.source,
                "target": result.target,
                "moved": result.moved,
                "processed_outputs_left": result.processed_outputs_left,
            }
        except dm.MoveError as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Upload not moved"),
                status_code=e.status,
            )
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Upload not moved"),
                status_code=500,
            )
