from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from gemini.api.site import Site
from gemini.rest_api.models import SiteInput, SiteOutput, RESTAPIError, SiteUpdate, str_to_dict, JSONB
from gemini.rest_api.models import ExperimentOutput, PlotOutput

from typing import List, Annotated, Optional

class SiteController(Controller):

    # Get All Sites
    @get(path="/all", sync_to_thread=True)
    def get_all_sites(self, limit: int = 100, offset: int = 0) -> List[SiteOutput]:
        try:
            sites = Site.get_all(limit=limit, offset=offset)
            if sites is None:
                error = RESTAPIError(
                    error="No sites found",
                    error_description="No sites were found"
                )
                return Response(content=error, status_code=404)
            return sites
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all sites"
            )
            return Response(content=error, status_code=500)

    # Get Sites
    @get(sync_to_thread=True)
    def get_sites(
        self,
        site_name: Optional[str] = None,
        site_city: Optional[str] = None,
        site_state: Optional[str] = None,
        site_country: Optional[str] = None,
        site_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = 'Experiment A'
    ) -> List[SiteOutput]:
        try:
            if site_info is not None:
                site_info = str_to_dict(site_info)

            sites = Site.search(
                site_name=site_name,
                site_city=site_city,
                site_state=site_state,
                site_country=site_country,
                site_info=site_info,
                experiment_name=experiment_name
            )
            if sites is None:
                error = RESTAPIError(
                    error="No sites found",
                    error_description="No sites were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return sites
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving sites"
            )
            return Response(content=error_message, status_code=500)
        
    # Get Site by ID
    @get(path="/id/{site_id:str}", sync_to_thread=True)
    def get_site_by_id(
        self, site_id: str
    ) -> SiteOutput:
        try:
            site = Site.get_by_id(id=site_id)
            if site is None:
                error = RESTAPIError(
                    error="Site not found",
                    error_description="The site with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return site
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the site"
            )
            return Response(content=error_message, status_code=500)
        
    # Create Site
    @post(sync_to_thread=True)
    def create_site(
        self,
        data: Annotated[SiteInput, Body]
    ) -> SiteOutput:
        try:
            site = Site.create(
                site_name=data.site_name,
                site_city=data.site_city,
                site_state=data.site_state,
                site_country=data.site_country,
                site_info=data.site_info,
                experiment_name=data.experiment_name
            )
            if site is None:
                error = RESTAPIError(
                    error="Site not created",
                    error_description="The site was not created"
                )
                return Response(content=error, status_code=500)
            return site
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the site"
            )
            return Response(content=error_message, status_code=500)


    # Update Site
    @patch(path="/id/{site_id:str}", sync_to_thread=True)
    def update_site(
        self,
        site_id: str,
        data: Annotated[SiteUpdate, Body]
    ) -> SiteOutput:
        try:
            site = Site.get_by_id(id=site_id)
            if site is None:
                error = RESTAPIError(
                    error="Site not found",
                    error_description="The site with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            site = site.update(
                site_name=data.site_name,
                site_city=data.site_city,
                site_state=data.site_state,
                site_country=data.site_country,
                site_info=data.site_info
            )
            return site
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the site"
            )
            return Response(content=error_message, status_code=500)
        
    # Delete Site
    @delete(path="/id/{site_id:str}", sync_to_thread=True)
    def delete_site(
        self, site_id: str
    ) -> None:
        try:
            site = Site.get_by_id(id=site_id)
            if site is None:
                error = RESTAPIError(
                    error="Site not found",
                    error_description="The site with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = site.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Failed to delete site",
                    error_description="The site could not be deleted"
                )
                return Response(content=error, status_code=500)
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the site"
            )
            return Response(content=error_message, status_code=500)
        

    # Get Associated Experiments
    @get(path="/id/{site_id:str}/experiments", sync_to_thread=True)
    def get_experiments_by_site_id(
        self, site_id: str
    ) -> List[ExperimentOutput]:
        try:
            site = Site.get_by_id(id=site_id)
            if site is None:
                error = RESTAPIError(
                    error="Site not found",
                    error_description="The site with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            experiments = site.get_associated_experiments()
            if experiments is None:
                error = RESTAPIError(
                    error="No experiments found",
                    error_description="No experiments were found for the given site ID"
                )
                return Response(content=error, status_code=404)
            return experiments
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving experiments for the site"
            )
            return Response(content=error_message, status_code=500)
        
    # Get Associated Plots
    @get(path="/id/{site_id:str}/plots", sync_to_thread=True)
    def get_plots_by_site_id(
        self, site_id: str
    ) -> List[PlotOutput]:
        try:
            site = Site.get_by_id(id=site_id)
            if site is None:
                error = RESTAPIError(
                    error="Site not found",
                    error_description="The site with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plots = site.get_associated_plots()
            if plots is None:
                error = RESTAPIError(
                    error="No plots found",
                    error_description="No plots were found for the given site ID"
                )
                return Response(content=error, status_code=404)
            return plots
        except Exception as e:
            error_message = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving plots for the site"
            )
            return Response(content=error_message, status_code=500)

