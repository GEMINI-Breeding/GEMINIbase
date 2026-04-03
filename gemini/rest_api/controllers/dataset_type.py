from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.dataset_type import DatasetType
from gemini.rest_api.models import (
    DatasetTypeInput, 
    DatasetTypeOutput,
    DatasetTypeUpdate, 
    RESTAPIError, 
    str_to_dict, 
    JSONB
)

from typing import List, Annotated, Optional

class DatasetTypeController(Controller):

    # Get All Dataset Types
    @get(path="/all", sync_to_thread=True)
    def get_all_dataset_types(self, limit: int = 100, offset: int = 0) -> List[DatasetTypeOutput]:
        try:
            dataset_types = DatasetType.get_all(limit=limit, offset=offset)
            if dataset_types is None:
                error = RESTAPIError(
                    error="No dataset types found",
                    error_description="No dataset types were found"
                )
                return Response(content=error, status_code=404)
            return dataset_types
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all dataset types"
            )
            return Response(content=error, status_code=500)

    # Get Dataset Types
    @get(sync_to_thread=True)
    def get_dataset_types(
        cls,
        dataset_type_name: Optional[str] = None,
        dataset_type_info: Optional[JSONB] = None
    ) -> List[DatasetTypeOutput]:
        try:
            if dataset_type_info is not None:
                dataset_type_info = str_to_dict(dataset_type_info)

            dataset_types = DatasetType.search(
                dataset_type_name=dataset_type_name,
                dataset_type_info=dataset_type_info
            )
            if dataset_types is None:
                error = RESTAPIError(
                    error="No dataset types found",
                    error_description="No dataset types were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return dataset_types
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving dataset types"
            )
            return Response(content=error, status_code=500)
        
    # Get Dataset Type by ID
    @get(path="/id/{dataset_type_id:int}", sync_to_thread=True)
    def get_dataset_type_by_id(
        cls, dataset_type_id: int
    ) -> DatasetTypeOutput:
        try:
            dataset_type = DatasetType.get_by_id(id=dataset_type_id)
            if dataset_type is None:
                error = RESTAPIError(
                    error="Dataset type not found",
                    error_description="The dataset type with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return dataset_type
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the dataset type"
            )
            return Response(content=error, status_code=500)
        
    # Create Dataset Type
    @post(sync_to_thread=True)
    def create_dataset_type(
        cls, data: Annotated[DatasetTypeInput, Body]
    ) -> DatasetTypeOutput:
        try:
            dataset_type = DatasetType.create(
                dataset_type_name=data.dataset_type_name,
                dataset_type_info=data.dataset_type_info
            )
            if dataset_type is None:
                error = RESTAPIError(
                    error="Dataset type not created",
                    error_description="The dataset type was not created"
                )
                return Response(content=error, status_code=500)
            return dataset_type
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the dataset type"
            )
            return Response(content=error, status_code=500)
        
    # Update Dataset Type
    @patch(path="/id/{dataset_type_id:int}", sync_to_thread=True)
    def update_dataset_type(
        cls, dataset_type_id: int, data: Annotated[DatasetTypeUpdate, Body]
    ) -> DatasetTypeOutput:
        try:
            dataset_type = DatasetType.get_by_id(id=dataset_type_id)
            if dataset_type is None:
                error = RESTAPIError(
                    error="Dataset type not found",
                    error_description="The dataset type with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            dataset_type = dataset_type.update(
                dataset_type_name=data.dataset_type_name,
                dataset_type_info=data.dataset_type_info
            )
            if dataset_type is None:
                error = RESTAPIError(
                    error="Dataset type not updated",
                    error_description="The dataset type could not be updated"
                )
                return Response(content=error, status_code=500)
            return dataset_type
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the dataset type"
            )
            return Response(content=error, status_code=500)
        
    # Delete Dataset Type
    @delete(path="/id/{dataset_type_id:int}", sync_to_thread=True)
    def delete_dataset_type(
        cls, dataset_type_id: int
    ) -> None:
        try:
            dataset_type = DatasetType.get_by_id(id=dataset_type_id)
            if dataset_type is None:
                error = RESTAPIError(
                    error="Dataset type not found",
                    error_description="The dataset type with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = dataset_type.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Dataset type not deleted",
                    error_description="The dataset type could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the dataset type"
            )
            return Response(content=error, status_code=500)


            
    



