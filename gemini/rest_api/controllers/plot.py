from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from pydantic import BaseModel

from gemini.api.plot import Plot
from gemini.rest_api.models import (
    PlotInput,
    PlotOutput,
    PlotUpdate,
    PlotBulkInput,
    PlotBulkResponse,
    RESTAPIError,
    JSONB,
    str_to_dict,
)
from gemini.rest_api.models import (
    AccessionOutput,
    PopulationOutput,
    ExperimentOutput,
    SeasonOutput,
    SiteOutput
)

from typing import List, Annotated, Optional


class PlotController(Controller):

    # Get All Plots
    @get(path="/all", sync_to_thread=True)
    def get_all_plots(self, limit: int = 100, offset: int = 0) -> List[PlotOutput]:
        try:
            plots = Plot.get_all(limit=limit, offset=offset)
            return plots or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all plots"
            )
            return Response(content=error, status_code=500)

    # Get Plots
    @get(sync_to_thread=True)
    def get_plots(
        self,
        plot_number: Optional[int] = None,
        plot_row_number: Optional[int] = None,
        plot_column_number: Optional[int] = None,
        experiment_name: Optional[str] = None,
        season_name: Optional[str] = None,
        site_name: Optional[str] = None
    ) -> List[PlotOutput]:
        try:

            plots = Plot.search(
                plot_number=plot_number,
                plot_row_number=plot_row_number,
                plot_column_number=plot_column_number,
                experiment_name=experiment_name,
                season_name=season_name,
                site_name=site_name
            )

            return plots or []
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving plots"
            )
            return Response(content=error, status_code=500)
        
    # Get Plot by ID
    @get(path="/id/{plot_id:str}", sync_to_thread=True)
    def get_plot_by_id(
        self, plot_id: str
    ) -> PlotOutput:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                error = RESTAPIError(
                    error="Plot not found",
                    error_description="The plot with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return plot
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving plot"
            )
            return Response(content=error, status_code=500)

    # Create a new Plot
    @post(sync_to_thread=True)
    def create_plot(
        self,
        data: Annotated[PlotInput, Body]
    ) -> PlotOutput:
        try:
            plot = Plot.create(
                plot_number=data.plot_number,
                plot_row_number=data.plot_row_number,
                plot_column_number=data.plot_column_number,
                plot_info=data.plot_info,
                experiment_name=data.experiment_name,
                season_name=data.season_name,
                site_name=data.site_name,
                accession_name=data.accession_name,
                population_name=data.population_name,
            )
            if plot is None:
                error = RESTAPIError(
                    error="Plot not created",
                    error_description="The plot was not created"
                )
                return Response(content=error, status_code=500)
            return plot
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the plot"
            )
            return Response(content=error, status_code=500)
        
    # Bulk-create Plots
    #
    # The import wizard pre-creates thousands of plots before ingesting
    # trait records. The single-plot POST route resolves five name-keyed
    # FKs per request (experiment/season/site/accession/population), so
    # a 3k-plot spreadsheet fired ~20k queries across ~3k HTTP round
    # trips. This endpoint collapses that into 5 batched SELECTs plus one
    # INSERT ... ON CONFLICT DO NOTHING.
    @post(path="/bulk", sync_to_thread=True)
    def create_plots_bulk(
        self,
        data: Annotated[PlotBulkInput, Body]
    ) -> PlotBulkResponse:
        try:
            plot_dicts = [p.model_dump() for p in data.plots]
            success, submitted, skipped = Plot.create_bulk(plot_dicts)
            if not success:
                error = RESTAPIError(
                    error="Bulk plot creation failed",
                    error_description="The plots could not be created"
                )
                return Response(content=error, status_code=500)
            return PlotBulkResponse(submitted_count=submitted, skipped_count=skipped)
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while bulk-creating plots"
            )
            return Response(content=error, status_code=500)

    # Plot geometry — GeoJSON FeatureCollection scoped to one
    # (experiment, season, site). Powers the analyze-page geospatial
    # viewer. Reads plots.plot_geometry_info populated by
    # PlotGeometryVersion.save()/.activate() materialization. Plots
    # without a geometry are filtered out (no point returning them).
    @get(path="/geojson", sync_to_thread=True)
    def get_plots_geojson(
        self,
        experiment_id: str,
        season_id: str,
        site_id: str,
    ) -> dict:
        try:
            from sqlalchemy import select as _select
            from gemini.db.core.base import db_engine
            from gemini.db.models.plots import PlotModel

            with db_engine.get_session() as session:
                rows = (
                    session.execute(
                        _select(
                            PlotModel.id,
                            PlotModel.plot_number,
                            PlotModel.plot_row_number,
                            PlotModel.plot_column_number,
                            PlotModel.accession_id,
                            PlotModel.plot_geometry_info,
                        )
                        .where(PlotModel.experiment_id == experiment_id)
                        .where(PlotModel.season_id == season_id)
                        .where(PlotModel.site_id == site_id)
                    )
                    .all()
                )
            features = []
            for r in rows:
                geom_info = r.plot_geometry_info or {}
                if not isinstance(geom_info, dict):
                    continue
                geom = geom_info.get("geometry")
                if not isinstance(geom, dict):
                    continue
                stored_props = geom_info.get("properties") or {}
                if not isinstance(stored_props, dict):
                    stored_props = {}
                # Authoritative props come from the row; anything extra
                # the snapshot carried is preserved underneath.
                props = {
                    **stored_props,
                    "plot_id": str(r.id) if r.id is not None else None,
                    "plot_number": r.plot_number,
                    "plot_row_number": r.plot_row_number,
                    "plot_column_number": r.plot_column_number,
                    "accession_id": str(r.accession_id)
                    if r.accession_id is not None
                    else None,
                }
                features.append(
                    {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": props,
                    }
                )
            return {"type": "FeatureCollection", "features": features}
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while building plot GeoJSON",
            )
            return Response(content=error, status_code=500)

    # Update Plot
    @patch(path="/id/{plot_id:str}", sync_to_thread=True)
    def update_plot(
        self,
        plot_id: str,
        data: Annotated[PlotUpdate, Body]
    ) -> PlotOutput:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                error = RESTAPIError(
                    error="Plot not found",
                    error_description="The plot with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            plot = plot.update(
                plot_number=data.plot_number,
                plot_row_number=data.plot_row_number,
                plot_column_number=data.plot_column_number,
                plot_info=data.plot_info,
                plot_geometry_info=data.plot_geometry_info,
            )
            if plot is None:
                error = RESTAPIError(
                    error="Plot not updated",
                    error_description="The plot was not updated"
                )
                return Response(content=error, status_code=500)
            return plot
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the plot"
            )
            return Response(content=error, status_code=500)
        
    # Delete Plot
    @delete(path="/id/{plot_id:str}", sync_to_thread=True)
    def delete_plot(
        self, plot_id: str
    ) -> None:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                error = RESTAPIError(
                    error="Plot not found",
                    error_description="The plot with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = plot.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Failed to delete plot",
                    error_description="The plot was not deleted"
                )
                return Response(content=error, status_code=500)
            return None
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the plot"
            )
            return Response(content=error, status_code=500)
        
        
    @get(path="/id/{plot_id:str}/accession", sync_to_thread=True)
    def get_plot_accession(self, plot_id: str) -> AccessionOutput:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                return Response(content=RESTAPIError(error="Plot not found", error_description=""), status_code=404)
            accession = plot.get_accession()
            if accession is None:
                return Response(content=RESTAPIError(error="No accession", error_description="").to_html(), status_code=404)
            return accession
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)

    @get(path="/id/{plot_id:str}/population", sync_to_thread=True)
    def get_plot_population(self, plot_id: str) -> PopulationOutput:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                return Response(content=RESTAPIError(error="Plot not found", error_description=""), status_code=404)
            population = plot.get_population()
            if population is None:
                return Response(content=RESTAPIError(error="No population", error_description="").to_html(), status_code=404)
            return population
        except Exception as e:
            return Response(content=RESTAPIError(error=str(e), error_description=""), status_code=500)
        
    # Get Plot Experiment
    @get(path="/id/{plot_id:str}/experiment", sync_to_thread=True)
    def get_plot_experiment(
        self, plot_id: str
    ) -> ExperimentOutput:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                error = RESTAPIError(
                    error="Plot not found",
                    error_description="The plot with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            experiment = plot.get_associated_experiment()
            if experiment is None:
                error = RESTAPIError(
                    error="Experiment not found",
                    error_description="The experiment for the given plot was not found"
                )
                return Response(content=error, status_code=404)
            return experiment
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the experiment for the plot"
            )
            return Response(content=error, status_code=500)
        
    # Get Plot Season
    @get(path="/id/{plot_id:str}/season", sync_to_thread=True)
    def get_plot_season(
        self, plot_id: str
    ) -> SeasonOutput:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                error = RESTAPIError(
                    error="Plot not found",
                    error_description="The plot with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            season = plot.get_associated_season()
            if season is None:
                error = RESTAPIError(
                    error="Season not found",
                    error_description="The season for the given plot was not found"
                )
                return Response(content=error, status_code=404)
            return season
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the season for the plot"
            )
            return Response(content=error, status_code=500)
        
    # Get Plot Site
    @get(path="/id/{plot_id:str}/site", sync_to_thread=True)
    def get_plot_site(
        self, plot_id: str
    ) -> SiteOutput:
        try:
            plot = Plot.get_by_id(id=plot_id)
            if plot is None:
                error = RESTAPIError(
                    error="Plot not found",
                    error_description="The plot with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            site = plot.get_associated_site()
            if site is None:
                error = RESTAPIError(
                    error="Site not found",
                    error_description="The site for the given plot was not found"
                )
                return Response(content=error, status_code=404)
            return site
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving the site for the plot"
            )
            return Response(content=error, status_code=500)

