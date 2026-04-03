from litestar import Response
from litestar.handlers import get, post, patch, delete
from litestar.params import Body
from litestar.controller import Controller

from pydantic import BaseModel

from gemini.api.sensor_platform import SensorPlatform
from gemini.api.enums import GEMINISensorType, GEMINIDataFormat, GEMINIDataType
from gemini.rest_api.models import SensorPlatformInput, SensorPlatformOutput, SensorPlatformUpdate, RESTAPIError, JSONB, str_to_dict
from gemini.rest_api.models import SensorOutput, ExperimentOutput
from typing import List, Annotated, Optional

class SensorPlatformSensorInput(BaseModel):
    sensor_name: str
    sensor_type_id: int
    sensor_data_type_id: int
    sensor_data_format_id: int
    sensor_info: Optional[JSONB] = None
    experiment_name: Optional[str] = 'Experiment A'


class SensorPlatformController(Controller):

    # Get All Sensor Platforms
    @get(path="/all", sync_to_thread=True)
    def get_all_sensor_platforms(self, limit: int = 100, offset: int = 0) -> List[SensorPlatformOutput]:
        try:
            sensor_platforms = SensorPlatform.get_all(limit=limit, offset=offset)
            if sensor_platforms is None:
                error = RESTAPIError(
                    error="No sensor platforms found",
                    error_description="No sensor platforms were found"
                )
                return Response(content=error, status_code=404)
            return sensor_platforms
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving all sensor platforms"
            )
            return Response(content=error, status_code=500)

    # Get Sensor Platforms
    @get(sync_to_thread=True)
    def get_sensor_platforms(
        self,
        sensor_platform_name: Optional[str] = None,
        sensor_platform_info: Optional[JSONB] = None,
        experiment_name: Optional[str] = 'Experiment A'
    ) -> List[SensorPlatformOutput]:
        try:
            if sensor_platform_info is not None:
                sensor_platform_info = str_to_dict(sensor_platform_info)

            sensor_platforms = SensorPlatform.search(
                sensor_platform_name=sensor_platform_name,
                sensor_platform_info=sensor_platform_info,
                experiment_name=experiment_name
            )

            if sensor_platforms is None:
                error = RESTAPIError(
                    error="No sensor platforms found",
                    error_description="No sensor platforms were found with the given search criteria"
                )
                return Response(content=error, status_code=404)
            return sensor_platforms
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving sensor platforms"
            )
            return Response(content=error, status_code=500)
        

    # Get Sensor Platform by ID
    @get(path="/id/{sensor_platform_id:str}", sync_to_thread=True)
    def get_sensor_platform_by_id(
        self, sensor_platform_id: str
    ) -> SensorPlatformOutput:
        try:
            sensor_platform = SensorPlatform.get_by_id(id=sensor_platform_id)
            if sensor_platform is None:
                error = RESTAPIError(
                    error="Sensor platform not found",
                    error_description="The sensor platform with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            return sensor_platform
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving sensor platforms"
            )
            return Response(content=error, status_code=500)
        
    # Create Sensor Platform
    @post(sync_to_thread=True)
    def create_sensor_platform(
        self,
        data: Annotated[SensorPlatformInput, Body]
    ) -> SensorPlatformOutput:
        try:
            sensor_platform = SensorPlatform.create(
                sensor_platform_name=data.sensor_platform_name,
                sensor_platform_info=data.sensor_platform_info,
                experiment_name=data.experiment_name
            )
            if sensor_platform is None:
                error = RESTAPIError(
                    error="Sensor platform not created",
                    error_description="The sensor platform was not created"
                )
                return Response(content=error, status_code=500)
            return sensor_platform
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while creating the sensor platform"
            )
            return Response(content=error, status_code=500)
        
    # Update Sensor Platform
    @patch(path="/id/{sensor_platform_id:str}", sync_to_thread=True)
    def update_sensor_platform(
        self,
        sensor_platform_id: str,
        data: Annotated[SensorPlatformUpdate, Body]
    ) -> SensorPlatformOutput:
        try:
            sensor_platform = SensorPlatform.get_by_id(id=sensor_platform_id)
            if sensor_platform is None:
                error = RESTAPIError(
                    error="Sensor platform not found",
                    error_description="The sensor platform with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            sensor_platform = sensor_platform.update(
                sensor_platform_name=data.sensor_platform_name,
                sensor_platform_info=data.sensor_platform_info
            )
            if not sensor_platform:
                error = RESTAPIError(
                    error="Sensor platform not updated",
                    error_description="The sensor platform was not updated"
                )
                return Response(content=error, status_code=500)
            return sensor_platform
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while updating the sensor platform"
            )
            return Response(content=error, status_code=500)
        

    # Delete Sensor Platform
    @delete(path="/id/{sensor_platform_id:str}", sync_to_thread=True)
    def delete_sensor_platform(
        self, sensor_platform_id: str
    ) -> None:
        try:
            sensor_platform = SensorPlatform.get_by_id(id=sensor_platform_id)
            if sensor_platform is None:
                error = RESTAPIError(
                    error="Sensor platform not found",
                    error_description="The sensor platform with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            is_deleted = sensor_platform.delete()
            if not is_deleted:
                error = RESTAPIError(
                    error="Sensor platform not deleted",
                    error_description="The sensor platform was not deleted"
                )
                return Response(content=error, status_code=500)
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while deleting the sensor platform"
            )
            return Response(content=error, status_code=500)
        
    # Get Experiments for Sensor Platform
    @get(path="/id/{sensor_platform_id:str}/experiments", sync_to_thread=True)
    def get_experiments_for_sensor_platform(
        self, sensor_platform_id: str
    ) -> List[ExperimentOutput]:
        try:
            sensor_platform = SensorPlatform.get_by_id(id=sensor_platform_id)
            if sensor_platform is None:
                error = RESTAPIError(
                    error="Sensor platform not found",
                    error_description="The sensor platform with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            experiments = sensor_platform.get_associated_experiments()
            if experiments is None:
                error = RESTAPIError(
                    error="No experiments found",
                    error_description="No experiments were found for the given sensor platform"
                )
                return Response(content=error, status_code=404)
            return experiments
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving experiments"
            )
            return Response(content=error, status_code=500)
            
    # Get Sensors for Sensor Platform
    @get(path="/id/{sensor_platform_id:str}/sensors", sync_to_thread=True)
    def get_sensors_for_sensor_platform(
        self, sensor_platform_id: str
    ) -> List[SensorOutput]:
        try:
            sensor_platform = SensorPlatform.get_by_id(id=sensor_platform_id)
            if sensor_platform is None:
                error = RESTAPIError(
                    error="Sensor platform not found",
                    error_description="The sensor platform with the given ID was not found"
                )
                return Response(content=error, status_code=404)
            sensors = sensor_platform.get_associated_sensors()
            if sensors is None:
                error = RESTAPIError(
                    error="No sensors found",
                    error_description="No sensors were found for the given sensor platform"
                )
                return Response(content=error, status_code=404)
            return sensors
        except Exception as e:
            error = RESTAPIError(
                error=str(e),
                error_description="An error occurred while retrieving sensors"
            )
            return Response(content=error, status_code=500)
        
