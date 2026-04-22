from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller
from litestar.response import Stream
from litestar.serialization import encode_json
from litestar.enums import RequestEncodingType

from pydantic import BaseModel

from collections.abc import AsyncGenerator, Generator

from sqlalchemy.exc import DBAPIError

from gemini.api.trait import Trait, GEMINITraitLevel
from gemini.api.trait_record import TraitRecord
from gemini.rest_api.models import TraitInput, TraitOutput, TraitUpdate, JSONB, str_to_dict
from gemini.rest_api.models import TraitRecordInput, TraitRecordOutput, TraitRecordUpdate, TraitLevelSearch
from gemini.rest_api.models import TraitRecordBulkInput, TraitRecordBulkOutput
from gemini.rest_api.models import RESTAPIError
from gemini.rest_api.models import DatasetOutput
from typing import List, Annotated, Optional

from gemini.rest_api.models import (
    TraitRecordInput,
    TraitRecordOutput,
    TraitRecordUpdate
)


async def trait_records_bytes_generator(trait_record_generator: Generator[TraitRecord, None, None]) -> AsyncGenerator[bytes, None]:
    for record in trait_record_generator:
        record = record.model_dump(exclude_none=True)
        record = encode_json(record) + b'\n'
        yield record


class TraitDatasetInput(BaseModel):
    dataset_name: str
    dataset_info: Optional[JSONB] = None
    collection_date: Optional[str] = None
    experiment_name: Optional[str] = 'Experiment A'



class TraitController(Controller):

    # Get All Traits
    @get(path="/all", sync_to_thread=True)
    def get_all_traits(self, limit: int = 100, offset: int = 0) -> List[TraitOutput]:
        try:
            traits = Trait.get_all(limit=limit, offset=offset)
            return traits or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all traits"
            )
            return Response(content=error, status_code=500)

    # Get Traits
    @get(sync_to_thread=True)
    def get_traits(
        self,
        trait_name: Optional[str] = None,
        trait_units: Optional[str] = None,
        trait_level_id: Optional[int] = None,
        trait_info: Optional[JSONB] = None,
        trait_metrics: Optional[JSONB] = None,
        experiment_name: Optional[str] = 'Experiment A'
    ) -> List[TraitOutput]:
        try:
            if trait_info is not None:
                trait_info = str_to_dict(trait_info)
            if trait_metrics is not None:
                trait_metrics = str_to_dict(trait_metrics)

            traits = Trait.search(
                trait_name=trait_name,
                trait_units=trait_units,
                trait_level=GEMINITraitLevel(trait_level_id) if trait_level_id else None,
                trait_info=trait_info,
                trait_metrics=trait_metrics,
                experiment_name=experiment_name
            )
            return traits or []
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving traits"
            )
            return Response(content=error_message, status_code=500)
        
    # Get Trait by ID
    @get(path="/id/{trait_id:str}", sync_to_thread=True)
    def get_trait_by_id(
        self, trait_id: str
    ) -> TraitOutput:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return trait
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving trait"
            )
            return Response(content=error_message, status_code=500)
        
    # Create Trait
    @post(sync_to_thread=True)
    def create_trait(
        self,
        data: Annotated[TraitInput, Body]
    ) -> TraitOutput:
        try:
            trait = Trait.create(
                trait_name=data.trait_name,
                trait_units=data.trait_units,
                trait_level=GEMINITraitLevel(data.trait_level_id),
                trait_info=data.trait_info,
                trait_metrics=data.trait_metrics,
                experiment_name=data.experiment_name,
            )
            if trait is None:
                error = RESTAPIError(
                    error="An error occurred while creating trait",
                    error_description="An error occurred while creating trait"
                )
                return Response(content=error, status_code=500)
            return trait
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating trait"
            )
            return Response(content=error_message, status_code=500)
        
    # Update Trait
    @patch(path="/id/{trait_id:str}", sync_to_thread=True)
    def update_trait(
        self,
        trait_id: str,
        data: Annotated[TraitUpdate, Body]
    ) -> TraitOutput:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            trait = trait.update(
                trait_name=data.trait_name,
                trait_units=data.trait_units,
                trait_level=GEMINITraitLevel(data.trait_level_id) if data.trait_level_id else None,
                trait_info=data.trait_info,
                trait_metrics=data.trait_metrics,
            )
            if trait is None:
                error = RESTAPIError(
                    error="An error occurred while updating trait",
                    error_description="An error occurred while updating trait"
                )
                return Response(content=error, status_code=500)
            return trait
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating trait"
            )
            return Response(content=error_message, status_code=500)
        
    # Delete Trait
    @delete(path="/id/{trait_id:str}", sync_to_thread=True)
    def delete_trait(
        self, trait_id: str
    ) -> None:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = trait.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Failed to delete trait",
                    error_description="The trait was not deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting trait"
            )
            return Response(content=error_message, status_code=500)
        
    # Get Trait Experiments
    @get(path="/id/{trait_id:str}/experiments", sync_to_thread=True)
    def get_trait_experiments(
        self, trait_id: str
    ) -> List[str]:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return trait.get_associated_experiments() or []
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving trait experiments"
            )
            return Response(content=error_message, status_code=500)

    # Get Trait Datasets
    @get(path="/id/{trait_id:str}/datasets", sync_to_thread=True)
    def get_trait_datasets(
        self, trait_id: str
    ) -> List[DatasetOutput]:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return trait.get_associated_datasets() or []
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving trait datasets"
            )
            return Response(content=error_message, status_code=500)
        
    # Add Trait Record
    @post(path="/id/{trait_id:str}/records", sync_to_thread=True)
    def add_trait_record(
        self,
        trait_id: str,
        data: Annotated[TraitRecordInput, Body(media_type=RequestEncodingType.MULTI_PART)]
    ) -> TraitRecordOutput:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)

            add_success, inserted_record_ids = trait.insert_record(
                timestamp=data.timestamp,
                collection_date=data.collection_date,
                trait_value=data.trait_value,
                dataset_name=data.dataset_name,
                experiment_name=data.experiment_name,
                season_name=data.season_name,
                site_name=data.site_name,
                plot_number=data.plot_number,
                plot_row_number=data.plot_row_number,
                plot_column_number=data.plot_column_number,
                record_info=data.record_info
            )
            if not add_success:
                error = RESTAPIError(
                    error="Failed to add trait record",
                    error_description="The trait record was not added"
                )
                return Response(content=error, status_code=500)
            inserted_record_id = inserted_record_ids[0]
            inserted_trait_record = TraitRecord.get_by_id(id=inserted_record_id)
            if inserted_trait_record is None:
                error = RESTAPIError(
                    error="Trait record not found",
                    error_description="The trait record with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return inserted_trait_record
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while adding trait record"
            )
            return Response(content=error_message, status_code=500)

    # Bulk Add Trait Records
    @post(path="/id/{trait_id:str}/records/bulk", sync_to_thread=True)
    def bulk_add_trait_records(
        self,
        trait_id: str,
        data: TraitRecordBulkInput
    ) -> TraitRecordBulkOutput:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                return Response(
                    content=RESTAPIError(error="Trait not found", error_description="The trait with the given ID was not found"),
                    status_code=404,
                )

            from datetime import datetime as dt

            timestamps = []
            trait_values = []
            plot_numbers = []
            plot_row_numbers = []
            plot_column_numbers = []
            record_infos = []

            for row in data.records:
                ts = row.get('timestamp')
                if isinstance(ts, str):
                    ts = dt.fromisoformat(ts.replace('Z', '+00:00'))
                timestamps.append(ts)
                trait_values.append(float(row['trait_value']))
                plot_numbers.append(row.get('plot_number'))
                plot_row_numbers.append(row.get('plot_row_number'))
                plot_column_numbers.append(row.get('plot_column_number'))
                record_infos.append(row.get('record_info', {}))

            success, record_ids = trait.insert_records(
                timestamps=timestamps,
                collection_date=data.collection_date,
                trait_values=trait_values,
                dataset_name=data.dataset_name,
                experiment_name=data.experiment_name,
                season_name=data.season_name,
                site_name=data.site_name,
                plot_numbers=plot_numbers if any(p is not None for p in plot_numbers) else None,
                plot_row_numbers=plot_row_numbers if any(p is not None for p in plot_row_numbers) else None,
                plot_column_numbers=plot_column_numbers if any(p is not None for p in plot_column_numbers) else None,
                record_info=record_infos,
            )

            if not success:
                return Response(
                    content=RESTAPIError(error="Bulk insert failed", error_description="Failed to insert trait records"),
                    status_code=500,
                )

            return TraitRecordBulkOutput(
                inserted_count=len(record_ids),
                record_ids=[str(rid) for rid in record_ids],
            )
        except DBAPIError:
            # Let the app-level handler surface the Postgres message
            # (e.g. trigger RAISE, constraint violation) as a structured 422.
            raise
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="An error occurred during bulk trait record insert"),
                status_code=500,
            )

    # Search Trait Records
    @get(path="/id/{trait_id:str}/records", sync_to_thread=True)
    def search_trait_records(
        self,
        trait_id: str,
        experiment_name: Optional[str] = None,
        season_name: Optional[str] = None,
        site_name: Optional[str] = None,
        plot_number: Optional[int] = None,
        plot_row_number: Optional[int] = None,
        plot_column_number: Optional[int] = None,
        collection_date: Optional[str] = None
    ) -> Stream:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            trait_records = trait.search_records(
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name,
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                collection_date=collection_date
            )
            return Stream(trait_records_bytes_generator(trait_records), media_type="application/ndjson")
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving trait records"
            )
            return Response(content=error_message, status_code=500)
        
    @get(path="/id/{trait_id:str}/records/filter", sync_to_thread=True)
    def filter_trait_records(
        self,
        trait_id: str,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
        dataset_names: Optional[List[str]] = None,
        experiment_names: Optional[List[str]] = None,
        season_names: Optional[List[str]] = None,
        site_names: Optional[List[str]] = None
    ) -> Stream:
        try:
            trait = Trait.get_by_id(id=trait_id)
            if trait is None:
                error = RESTAPIError(
                    error="Trait not found",
                    error_description="The trait with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            trait_records = trait.filter_records(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                dataset_names=dataset_names,
                experiment_names=experiment_names,
                season_names=season_names,
                site_names=site_names
            )
            return Stream(trait_records_bytes_generator(trait_records), media_type="application/ndjson")
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while filtering trait records"
            )
            return Response(content=error, status_code=500)
        
    # Get Trait Record by ID
    @get(path="/records/id/{trait_record_id:str}", sync_to_thread=True)
    def get_trait_record_by_id(
        self, trait_record_id: str
    ) -> TraitRecordOutput:
        try:
            trait_record = TraitRecord.get_by_id(id=trait_record_id)
            if trait_record is None:
                error = RESTAPIError(
                    error="Trait record not found",
                    error_description="The trait record with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return trait_record
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving trait record"
            )
            return Response(content=error_message, status_code=500)
        
    # Update Trait Record
    @patch(path="/records/id/{trait_record_id:str}", sync_to_thread=True)
    def update_trait_record(
        self,
        trait_record_id: str,
        data: Annotated[TraitRecordUpdate, Body]
    ) -> TraitRecordOutput:
        try:
            trait_record = TraitRecord.get_by_id(id=trait_record_id)
            if trait_record is None:
                error = RESTAPIError(
                    error="Trait record not found",
                    error_description="The trait record with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            trait_record = trait_record.update(
                trait_value=data.trait_value,
                record_info=data.record_info,
            )
            if trait_record is None:
                error = RESTAPIError(
                    error="An error occurred while updating trait record",
                    error_description="An error occurred while updating trait record"
                )
                return Response(content=error, status_code=500)
            return trait_record
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating trait record"
            )
            return Response(content=error_message, status_code=500)
        
    # Delete Trait Record
    @delete(path="/records/id/{trait_record_id:str}", sync_to_thread=True)
    def delete_trait_record(
        self, trait_record_id: str
    ) -> None:
        try:
            trait_record = TraitRecord.get_by_id(id=trait_record_id)
            if trait_record is None:
                error = RESTAPIError(
                    error="Trait record not found",
                    error_description="The trait record with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = trait_record.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Failed to delete trait record",
                    error_description="The trait record was not deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting trait record"
            )
            return Response(content=error_message, status_code=500)
