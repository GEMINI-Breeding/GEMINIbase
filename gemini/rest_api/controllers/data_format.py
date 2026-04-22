from litestar import Response
from litestar.plugins.pydantic import PydanticDTO
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.data_format import DataFormat
from gemini.rest_api.models import (
    DataFormatInput, 
    DataFormatOutput,
    DataFormatUpdate,
    DataTypeOutput, 
    RESTAPIError, 
    JSONB, 
    str_to_dict
) 

from typing import List, Annotated, Optional

class DataFormatController(Controller):


    # Get All Data Formats
    @get(path="/all", sync_to_thread=True)
    def get_all_data_formats(self, limit: int = 100, offset: int = 0) -> List[DataFormatOutput]:
        try:
            data_formats = DataFormat.get_all(limit=limit, offset=offset)
            return data_formats or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all data formats"
            )
            return Response(content=error, status_code=500)

    # Get Data Formats
    @get(sync_to_thread=True)
    def get_data_formats(
        cls,
        data_format_name: Optional[str] = None,
        data_format_mime_type: Optional[str] = None,
        data_format_info: Optional[JSONB] = None
    ) -> List[DataFormatOutput]:
        try:
            if data_format_info is not None:
                data_format_info = str_to_dict(data_format_info)

            data_formats = DataFormat.search(
                data_format_name=data_format_name,
                data_format_mime_type=data_format_mime_type,
                data_format_info=data_format_info
            )
            return data_formats or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving data formats"
            )
            return Response(content=error, status_code=500)

    # Get Data Format by ID
    @get(path="/id/{data_format_id:int}", sync_to_thread=True)
    def get_data_format_by_id(
        cls, data_format_id: int
    ) -> DataFormatOutput:
        try:
            data_format = DataFormat.get_by_id(id=data_format_id)
            if data_format is None:
                error = RESTAPIError(
                    error="Data format not found",
                    error_description="The data format with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return data_format
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the data format"
            )
            return Response(content=error, status_code=500)

        
    # Create a new Data Format
    @post(sync_to_thread=True)
    def create_data_format(
        cls, data: Annotated[DataFormatInput, Body]
    ) -> DataFormatOutput:
        try:
            data_format = DataFormat.create(
                data_format_name=data.data_format_name,
                data_format_mime_type=data.data_format_mime_type,
                data_format_info=data.data_format_info
            )
            if data_format is None:
                error = RESTAPIError(
                    error="Data format not created",
                    error_description="The data format could not be created"
                )
                return Response(content=error, status_code=500)
            return data_format
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the data format"
            )
            return Response(content=error, status_code=500)
        
    # Update Data Format
    @patch(path="/id/{data_format_id:int}", sync_to_thread=True)
    def update_data_format(
        cls, data_format_id: int, data: Annotated[DataFormatUpdate, Body]
    ) -> DataFormatOutput:
        try:
            data_format = DataFormat.get_by_id(id=data_format_id)
            if data_format is None:
                error_html = RESTAPIError(
                    error="Data format not found",
                    error_description="The data format with the given ID was not found"
                ).to_html()
                return Response(content=error_html, status_code=404)

            data_format = data_format.update(
                data_format_name=data.data_format_name,
                data_format_mime_type=data.data_format_mime_type,
                data_format_info=data.data_format_info
            )
            if data_format is None:
                error = RESTAPIError(
                    error="Data format not updated",
                    error_description="The data format could not be updated"
                )
                return Response(content=error, status_code=500)
            return data_format
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the data format"
            )
            return Response(content=error, status_code=500)
        
    # Delete Data Format
    @delete(path="/id/{data_format_id:int}", sync_to_thread=True)
    def delete_data_format(
        cls, data_format_id: int
    ) -> None:
        try:
            data_format = DataFormat.get_by_id(id=data_format_id)
            if data_format is None:
                error = RESTAPIError(
                    error="Data format not found",
                    error_description="The data format with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = data_format.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Data Format deletion failed",
                    error_description="The data format could not be deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the data format"
            )
            return Response(content=error, status_code=500)


    # Get Associated Data Types
    @get(path="/id/{data_format_id:int}/data_types", sync_to_thread=True)
    def get_associated_data_types(
        cls, data_format_id: int
    ) -> List[DataTypeOutput]:
        try:
            data_format = DataFormat.get_by_id(id=data_format_id)
            if data_format is None:
                error = RESTAPIError(
                    error="Data format not found",
                    error_description="The data format with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return data_format.get_associated_data_types() or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving associated data types"
            )
            return Response(content=error, status_code=500)



 