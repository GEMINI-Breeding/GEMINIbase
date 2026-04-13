from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.line import Line
from gemini.rest_api.models import LineInput, LineOutput, LineUpdate, RESTAPIError, str_to_dict, JSONB

from typing import List, Annotated, Optional


class LineController(Controller):

    @get(path="/all", sync_to_thread=True)
    def get_all_lines(self, limit: int = 100, offset: int = 0) -> List[LineOutput]:
        try:
            lines = Line.get_all(limit=limit, offset=offset)
            if lines is None:
                return Response(content=RESTAPIError(error="No lines found", error_description=""), status_code=404)
            return lines
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(sync_to_thread=True)
    def search_lines(self, line_name: Optional[str] = None, species: Optional[str] = None, line_info: Optional[JSONB] = None) -> List[LineOutput]:
        try:
            if line_info is not None:
                line_info = str_to_dict(line_info)
            lines = Line.search(line_name=line_name, species=species, line_info=line_info)
            if lines is None:
                return Response(content=RESTAPIError(error="No lines found", error_description=""), status_code=404)
            return lines
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{line_id:str}", sync_to_thread=True)
    def get_line_by_id(self, line_id: str) -> LineOutput:
        try:
            line = Line.get_by_id(id=line_id)
            if line is None:
                return Response(content=RESTAPIError(error="Line not found", error_description=""), status_code=404)
            return line
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @post(sync_to_thread=True)
    def create_line(self, data: Annotated[LineInput, Body]) -> LineOutput:
        try:
            line = Line.create(line_name=data.line_name, species=data.species, line_info=data.line_info)
            if line is None:
                return Response(content=RESTAPIError(error="Creation failed", error_description=""), status_code=500)
            return line
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @patch(path="/id/{line_id:str}", sync_to_thread=True)
    def update_line(self, line_id: str, data: Annotated[LineUpdate, Body]) -> LineOutput:
        try:
            line = Line.get_by_id(id=line_id)
            if line is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            line = line.update(line_name=data.line_name, species=data.species, line_info=data.line_info)
            if line is None:
                return Response(content=RESTAPIError(error="Update failed", error_description=""), status_code=500)
            return line
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @delete(path="/id/{line_id:str}", sync_to_thread=True)
    def delete_line(self, line_id: str) -> None:
        try:
            line = Line.get_by_id(id=line_id)
            if line is None:
                return Response(content=RESTAPIError(error="Not found", error_description="").to_html(), status_code=404)
            if not line.delete():
                return Response(content=RESTAPIError(error="Deletion failed", error_description=""), status_code=500)
            return None
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)
