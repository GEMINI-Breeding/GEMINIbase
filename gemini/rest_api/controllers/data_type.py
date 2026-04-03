from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.data_type import DataType
from gemini.rest_api.models import (
    DataTypeInput, 
    DataTypeOutput,
    DataTypeUpdate,
    DataFormatOutput,
    RESTAPIError, 
    JSONB, 
    str_to_dict
)

from typing import List, Annotated, Optional

class DataTypeController(Controller):
    
    # Get All Data Types
    @get(path="/all", sync_to_thread=True)
    def get_all_data_types(self, limit: int = 100, offset: int = 0) -> List[DataTypeOutput]:
        try:
            data_types = DataType.get_all(limit=limit, offset=offset)
            if data_types is None:
                error = RESTAPIError(
                    error="No data types found",
                    error_description="No data types were found"
                )
                return Response(content=error, status_code=404)
            return data_types
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all data types"
            )
            return Response(content=error, status_code=500)

    # Get Data Types
    @get(sync_to_thread=True)
    def get_data_types(
        self,
        data_type_name: Optional[str] = None,
        data_type_info: Optional[JSONB] = None
    ) -> List[DataTypeOutput]:
        try:
            if data_type_info is not None:
                data_type_info = str_to_dict(data_type_info)
            data_types = DataType.search(
                data_type_name=data_type_name,
                data_type_info=data_type_info
            )
            if data_types is None:
                error = RESTAPIError(
                    error="No data types found",
                    error_description="No data types were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return data_types
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving data types"
            )
            return Response(content=error, status_code=500)
        
    # Get Data Type by ID
    @get(path="/id/{data_type_id:int}", sync_to_thread=True)
    def get_data_type_by_id(
        self, data_type_id: int
    ) -> DataTypeOutput:
        try:
            data_type = DataType.get_by_id(id=data_type_id)
            if data_type is None:
                error = RESTAPIError(
                    error="Data type not found",
                    error_description="The data type with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return data_type
        except Exception as e:
            error= RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the data type"
            )
            return Response(content=error, status_code=500)
        
    # Create a new Data Type
    @post(sync_to_thread=True)
    def create_data_type(
        self, data: Annotated[DataTypeInput, Body]
    ) -> DataTypeOutput:
        try:
            data_type = DataType.create(
                data_type_name=data.data_type_name,
                data_type_info=data.data_type_info
            )
            if data_type is None:
                error= RESTAPIError(
                    error="Data type not created",
                    error_description="The data type was not created"
                )
                return Response(content=error, status_code=500)
            return data_type
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the data type"
            )
            return Response(content=error, status_code=500)
        

    # Update Data Type
    @patch(path="/id/{data_type_id:int}", sync_to_thread=True)
    def update_data_type(
        cls, data_type_id: int, data: Annotated[DataTypeUpdate, Body]
    ) -> DataTypeOutput:
        try:
            data_type = DataType.get_by_id(id=data_type_id)
            if data_type is None:
                error= RESTAPIError(
                    error="Data type not found",
                    error_description="The data type with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            data_type = data_type.update(
                data_type_name=data.data_type_name,
                data_type_info=data.data_type_info
            )
            if data_type is None:
                error= RESTAPIError(
                    error="Data type update failed",
                    error_description="The data type was not updated"
                )
                return Response(content=error, status_code=500)
            return data_type
        except Exception as e:
            error= RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the data type"
            )
            return Response(content=error, status_code=500)
        
    # Delete Data Type
    @delete(path="/id/{data_type_id:int}", sync_to_thread=True)
    def delete_data_type(
        cls, data_type_id: int
    ) -> None:
        try:
            data_type = DataType.get_by_id(id=data_type_id)
            if data_type is None:
                error = RESTAPIError(
                    error="Data type not found",
                    error_description="The data type with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = data_type.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Data type not deleted",
                    error_description="The data type could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the data type"
            )
            return Response(content=error, status_code=500)
        

    # Get associated Data Formats
    @get(path="/id/{data_type_id:int}/data_formats", sync_to_thread=True)
    def get_associated_data_formats(
        cls, data_type_id: int
    ) -> List[DataFormatOutput]:
        try:
            data_type = DataType.get_by_id(id=data_type_id)
            if data_type is None:
                error = RESTAPIError(
                    error="Data type not found",
                    error_description="The data type with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            data_formats = data_type.get_associated_data_formats()
            if data_formats is None:
                error = RESTAPIError(
                    error="No data formats found",
                    error_description="No data formats were found for the given data type"
                )
                return Response(content=error, status_code=404)
            return data_formats
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated data formats"
            )
            return Response(content=error, status_code=500)
        
    
