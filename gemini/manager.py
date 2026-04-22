import shutil
import subprocess, os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import docker
from docker import DockerClient
from docker.errors import DockerException
from pydantic import BaseModel, ConfigDict, PrivateAttr

from gemini.config.settings import GEMINISettings
from gemini.logger.interfaces import logger_provider
from gemini.logger.providers.redis_logger import RedisLogger
from gemini.storage.interfaces import storage_provider
from gemini.storage.providers.minio_storage import MinioStorageProvider


DOCKER_SETUP_HINT = (
    "GEMINI requires Docker. Make sure it is installed and running.\n"
    "Install guide: https://docs.docker.com/engine/install/\n"
    "\n"
    "macOS:   Docker Desktop, OrbStack, or Colima\n"
    "           https://www.docker.com/products/docker-desktop/\n"
    "           https://orbstack.dev/  |  https://github.com/abiosoft/colima\n"
    "Linux:   Docker Engine via your package manager, then:\n"
    "           sudo systemctl start docker\n"
    "Windows: Docker Desktop (WSL 2 backend)\n"
    "           https://docs.docker.com/desktop/install/windows-install/\n"
    "\n"
    "If already installed, make sure the daemon is running."
)


class DockerUnavailableError(RuntimeError):
    """Raised when the Docker CLI or daemon is not reachable."""

    def __init__(self, reason: str):
        super().__init__(f"{reason}\n\n{DOCKER_SETUP_HINT}")

class GEMINIComponentType(str, Enum):
    META = "meta"
    DB = "db"
    LOGGER = "logger"
    STORAGE = "storage"
    REST_API = "rest_api"
    SCHEDULER_DB = "scheduler_db"
    SCHEDULER_SERVER = "scheduler_server"

class GEMINIContainerInfo(BaseModel):
    id: str
    image: str
    name: str
    ip_address: str


class GEMINIManager(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    env_file_path : str = Path(__file__).parent / "pipeline" / ".env"
    compose_file_path : str = Path(__file__).parent / "pipeline" / "docker-compose.yaml"

    # Pipeline Settings
    pipeline_settings: GEMINISettings = GEMINISettings()

    docker_containers: dict[str, GEMINIContainerInfo] = {}

    _docker_client: Optional[DockerClient] = PrivateAttr(default=None)

    @property
    def docker_client(self) -> DockerClient:
        if self._docker_client is None:
            if shutil.which("docker") is None:
                raise DockerUnavailableError(
                    "The `docker` command was not found on your PATH."
                )
            try:
                self._docker_client = docker.from_env()
            except DockerException as e:
                raise DockerUnavailableError(
                    f"Could not connect to the Docker daemon ({e})."
                ) from e
        return self._docker_client

    def model_post_init(self, __context: Any) -> None:
        # Best-effort container scan — don't fail import/construction just
        # because Docker isn't up. Commands that need Docker will surface a
        # clear error when invoked.
        try:
            self.scan_containers()
        except DockerUnavailableError:
            pass
        return super().model_post_init(__context)

    def scan_containers(self) -> None:
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                container_info = container.attrs
                container_name = container_info["Name"].strip("/")
                container_image = container_info["Config"]["Image"]
                container_id = container_info["Id"]
                container_gemini_network = container_info["NetworkSettings"]["Networks"].get("gemini_network")
                container_ip = container_gemini_network["IPAddress"]

                self.docker_containers[container_name] = GEMINIContainerInfo(
                    id=container_id,
                    image=container_image,
                    name=container_name,
                    ip_address=container_ip
                )
        except DockerUnavailableError:
            # Let callers decide how to report it.
            raise
        except Exception as e:
            print(f"Error scanning containers: {e}")

    def save_settings(self) -> None:
        # Delete current settings if they exist
        self.delete_settings()
        # Create a new settings file
        current_settings = self.get_settings()
        current_settings.create_env_file(self.env_file_path)
        self.pipeline_settings = current_settings
        print(f"Settings saved to {self.env_file_path}")


    def get_settings(self) -> GEMINISettings:
        current_settings = GEMINISettings()
        return current_settings
    
    def set_setting(self, setting_name: str, setting_value: Any) -> None:
        current_settings = GEMINISettings()
        if hasattr(current_settings, setting_name):
            current_settings.set_setting(setting_name, setting_value)
            self.save_settings()
        else:
            raise KeyError(f"Setting {setting_name} does not exist in GEMINISettings.")
        

    
    def delete_settings(self) -> None:
        try:
            if not os.path.exists(self.env_file_path):
                print(f"Settings file {self.env_file_path} does not exist.")
                return
            os.remove(self.env_file_path)
            print(f"Settings file {self.env_file_path} deleted.")
        except Exception as e:
            print(f"Error deleting settings file: {e}")
    
    def _run_compose(self, *compose_args: str) -> bool:
        if shutil.which("docker") is None:
            raise DockerUnavailableError("The `docker` command was not found on your PATH.")
        # Preflight the daemon so we surface one clean hint instead of letting
        # a cryptic `docker` error reach the user on top of our own.
        if not self._daemon_reachable():
            raise DockerUnavailableError("The Docker daemon is not reachable.")
        cmd = [
            "docker", "compose",
            "-f", str(self.compose_file_path),
            "--env-file", str(self.env_file_path),
            *compose_args,
        ]
        try:
            subprocess.run(cmd, check=True)
            return True
        except FileNotFoundError as e:
            raise DockerUnavailableError("The `docker` command was not found on your PATH.") from e
        except subprocess.CalledProcessError:
            # compose ran and printed its own error; don't double up.
            return False

    def _daemon_reachable(self) -> bool:
        try:
            _ = self.docker_client
            return True
        except DockerUnavailableError:
            return False

    def build(self) -> bool:
        return self._run_compose("build")

    def rebuild(self) -> bool:
        return (
            self._run_compose("down", "--remove-orphans", "--volumes")
            and self._run_compose("build", "--no-cache")
            and self._run_compose("up", "--detach")
        )

    def start(self) -> bool:
        return self._run_compose("up", "--detach")

    def clean(self) -> bool:
        return self._run_compose("down", "--volumes", "--remove-orphans")

    def stop(self) -> bool:
        return self._run_compose("stop")


    def update(self) -> bool:
        try:
            # Get update.sh script
            update_script_path = Path(__file__).parent / "scripts" / "update.sh"
            subprocess.run(
                ["bash", str(update_script_path)],
                check=True
            )
            return True
        except Exception as e:
            print(e)
            return False

    def get_component_settings(self, component_type: GEMINIComponentType) -> dict:
        current_settings = self.get_settings()
        match component_type:
            case GEMINIComponentType.META:
                return {
                    "GEMINI_DEBUG": current_settings.GEMINI_DEBUG,
                    "GEMINI_TYPE": current_settings.GEMINI_TYPE,
                    "GEMINI_PUBLIC_DOMAIN": current_settings.GEMINI_PUBLIC_DOMAIN,
                    "GEMINI_PUBLIC_IP": current_settings.GEMINI_PUBLIC_IP
                }
            case GEMINIComponentType.DB:
                return {
                    "GEMINI_DB_CONTAINER_NAME": current_settings.GEMINI_DB_CONTAINER_NAME,
                    "GEMINI_DB_IMAGE_NAME": current_settings.GEMINI_DB_IMAGE_NAME,
                    "GEMINI_DB_USER": current_settings.GEMINI_DB_USER,
                    "GEMINI_DB_PASSWORD": current_settings.GEMINI_DB_PASSWORD,
                    "GEMINI_DB_HOSTNAME": current_settings.GEMINI_DB_HOSTNAME,
                    "GEMINI_DB_NAME": current_settings.GEMINI_DB_NAME,
                    "GEMINI_DB_PORT": current_settings.GEMINI_DB_PORT
                }
            case GEMINIComponentType.LOGGER:
                return {
                    "GEMINI_LOGGER_CONTAINER_NAME": current_settings.GEMINI_LOGGER_CONTAINER_NAME,
                    "GEMINI_LOGGER_IMAGE_NAME": current_settings.GEMINI_LOGGER_IMAGE_NAME,
                    "GEMINI_LOGGER_HOSTNAME": current_settings.GEMINI_LOGGER_HOSTNAME,
                    "GEMINI_LOGGER_PORT": current_settings.GEMINI_LOGGER_PORT,
                    "GEMINI_LOGGER_PASSWORD": current_settings.GEMINI_LOGGER_PASSWORD
                }
            case GEMINIComponentType.STORAGE:
                return {
                    "GEMINI_STORAGE_CONTAINER_NAME": current_settings.GEMINI_STORAGE_CONTAINER_NAME,
                    "GEMINI_STORAGE_IMAGE_NAME": current_settings.GEMINI_STORAGE_IMAGE_NAME,
                    "GEMINI_STORAGE_HOSTNAME": current_settings.GEMINI_STORAGE_HOSTNAME,
                    "GEMINI_STORAGE_PORT": current_settings.GEMINI_STORAGE_PORT,
                    "GEMINI_STORAGE_API_PORT": current_settings.GEMINI_STORAGE_API_PORT,
                    "GEMINI_STORAGE_ROOT_USER": current_settings.GEMINI_STORAGE_ROOT_USER,
                    "GEMINI_STORAGE_ROOT_PASSWORD": current_settings.GEMINI_STORAGE_ROOT_PASSWORD,
                    "GEMINI_STORAGE_ACCESS_KEY": current_settings.GEMINI_STORAGE_ACCESS_KEY,
                    "GEMINI_STORAGE_SECRET_KEY": current_settings.GEMINI_STORAGE_SECRET_KEY,
                    "GEMINI_STORAGE_BUCKET_NAME": current_settings.GEMINI_STORAGE_BUCKET_NAME
                }
            case GEMINIComponentType.REST_API:
                return {
                    "GEMINI_REST_API_CONTAINER_NAME": current_settings.GEMINI_REST_API_CONTAINER_NAME,
                    "GEMINI_REST_API_IMAGE_NAME": current_settings.GEMINI_REST_API_IMAGE_NAME,
                    "GEMINI_REST_API_HOSTNAME": current_settings.GEMINI_REST_API_HOSTNAME,
                    "GEMINI_REST_API_PORT": current_settings.GEMINI_REST_API_PORT
                }
            case GEMINIComponentType.SCHEDULER_DB:
                return {
                    "GEMINI_SCHEDULER_DB_CONTAINER_NAME": current_settings.GEMINI_SCHEDULER_DB_CONTAINER_NAME,
                    "GEMINI_SCHEDULER_DB_IMAGE_NAME": current_settings.GEMINI_SCHEDULER_DB_IMAGE_NAME,
                    "GEMINI_SCHEDULER_DB_HOSTNAME": current_settings.GEMINI_SCHEDULER_DB_HOSTNAME,
                    "GEMINI_SCHEDULER_DB_USER": current_settings.GEMINI_SCHEDULER_DB_USER,
                    "GEMINI_SCHEDULER_DB_PASSWORD": current_settings.GEMINI_SCHEDULER_DB_PASSWORD,
                    "GEMINI_SCHEDULER_DB_NAME": current_settings.GEMINI_SCHEDULER_DB_NAME,
                    "GEMINI_SCHEDULER_DB_PORT": current_settings.GEMINI_SCHEDULER_DB_PORT
                }
            case GEMINIComponentType.SCHEDULER_SERVER:
                return {
                    "GEMINI_SCHEDULER_SERVER_CONTAINER_NAME": current_settings.GEMINI_SCHEDULER_SERVER_CONTAINER_NAME,
                    "GEMINI_SCHEDULER_SERVER_IMAGE_NAME": current_settings.GEMINI_SCHEDULER_SERVER_IMAGE_NAME,
                    "GEMINI_SCHEDULER_SERVER_HOSTNAME": current_settings.GEMINI_SCHEDULER_SERVER_HOSTNAME,
                    "GEMINI_SCHEDULER_SERVER_PORT": current_settings.GEMINI_SCHEDULER_SERVER_PORT
                }
            case _:
                raise ValueError(f"Unknown settings type: {component_type}")

