from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.accession import Accession
from gemini.rest_api.models import AccessionInput, AccessionOutput, AccessionUpdate, RESTAPIError, str_to_dict, JSONB

from typing import List, Annotated, Optional


class AccessionController(Controller):

    @get(path="/all", sync_to_thread=True)
    def get_all_accessions(self, limit: int = 100, offset: int = 0) -> List[AccessionOutput]:
        try:
            accessions = Accession.get_all(limit=limit, offset=offset)
            return accessions or []
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(sync_to_thread=True)
    def search_accessions(
        self,
        accession_name: Optional[str] = None,
        species: Optional[str] = None,
        accession_info: Optional[JSONB] = None,
    ) -> List[AccessionOutput]:
        try:
            if accession_info is not None:
                accession_info = str_to_dict(accession_info)
            return Accession.search(accession_name=accession_name, species=species, accession_info=accession_info) or []
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{accession_id:str}", sync_to_thread=True)
    def get_accession_by_id(self, accession_id: str) -> AccessionOutput:
        try:
            accession = Accession.get_by_id(id=accession_id)
            if accession is None:
                return Response(content=RESTAPIError(error="Accession not found", error_description=""), status_code=404)
            return accession
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @post(sync_to_thread=True)
    def create_accession(self, data: Annotated[AccessionInput, Body]) -> AccessionOutput:
        try:
            accession = Accession.create(
                accession_name=data.accession_name,
                line_name=data.line_name,
                species=data.species,
                accession_info=data.accession_info,
                population_name=data.population_name,
            )
            if accession is None:
                return Response(content=RESTAPIError(error="Creation failed", error_description=""), status_code=500)
            return accession
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @patch(path="/id/{accession_id:str}", sync_to_thread=True)
    def update_accession(self, accession_id: str, data: Annotated[AccessionUpdate, Body]) -> AccessionOutput:
        try:
            accession = Accession.get_by_id(id=accession_id)
            if accession is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            accession = accession.update(accession_name=data.accession_name, species=data.species, accession_info=data.accession_info)
            if accession is None:
                return Response(content=RESTAPIError(error="Update failed", error_description=""), status_code=500)
            return accession
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @delete(path="/id/{accession_id:str}", sync_to_thread=True)
    def delete_accession(self, accession_id: str) -> None:
        try:
            accession = Accession.get_by_id(id=accession_id)
            if accession is None:
                return Response(content=RESTAPIError(error="Not found", error_description="").to_html(), status_code=404)
            if not accession.delete():
                return Response(content=RESTAPIError(error="Deletion failed", error_description=""), status_code=500)
            return None
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{accession_id:str}/populations", sync_to_thread=True)
    def get_associated_populations(self, accession_id: str) -> list:
        try:
            accession = Accession.get_by_id(id=accession_id)
            if accession is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            populations = accession.get_associated_populations()
            if not populations:
                return Response(content=RESTAPIError(error="No associated populations", error_description=""), status_code=404)
            return populations
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{accession_id:str}/plots", sync_to_thread=True)
    def get_associated_plots(self, accession_id: str) -> list:
        try:
            accession = Accession.get_by_id(id=accession_id)
            if accession is None:
                return Response(content=RESTAPIError(error="Not found", error_description=""), status_code=404)
            plots = accession.get_associated_plots()
            if not plots:
                return Response(content=RESTAPIError(error="No associated plots", error_description=""), status_code=404)
            return plots
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)
