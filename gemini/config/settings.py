from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from enum import Enum
from typing import Any
from dotenv import load_dotenv, find_dotenv, dotenv_values


class GEMINISettings(BaseSettings):


    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../pipeline/.env"),
        env_file_encoding="utf-8"
    )

    # Meta
    GEMINI_DEBUG : bool = False
    GEMINI_TYPE: str = "internal"
    GEMINI_PUBLIC_DOMAIN : str = ""
    GEMINI_PUBLIC_IP : str = ""

    # Database Configuration
    GEMINI_DB_CONTAINER_NAME : str = "geminibase-db"
    GEMINI_DB_IMAGE_NAME : str = "geminibase/db"
    GEMINI_DB_USER : str = "gemini"
    GEMINI_DB_PASSWORD : str = "gemini"
    GEMINI_DB_HOSTNAME : str = "geminibase-db"
    GEMINI_DB_NAME : str = "gemini"
    GEMINI_DB_PORT : int = 5432

    # Logger Configuration
    GEMINI_LOGGER_CONTAINER_NAME : str = "geminibase-logger"
    GEMINI_LOGGER_IMAGE_NAME : str = "geminibase/logger"
    GEMINI_LOGGER_HOSTNAME : str = "geminibase-logger"
    GEMINI_LOGGER_PORT : int = 6379
    GEMINI_LOGGER_PASSWORD : str = "gemini"

    # File Store Configuration
    GEMINI_STORAGE_CONTAINER_NAME : str = "geminibase-storage"
    GEMINI_STORAGE_IMAGE_NAME : str = "geminibase/storage"
    GEMINI_STORAGE_HOSTNAME : str = "geminibase-storage"
    GEMINI_STORAGE_PORT : int = 9000
    GEMINI_STORAGE_API_PORT : int = 9001
    GEMINI_STORAGE_ROOT_USER : str = "gemini_root"
    GEMINI_STORAGE_ROOT_PASSWORD : str = "gemini_root"
    GEMINI_STORAGE_BUCKET_NAME : str = "gemini"
    GEMINI_STORAGE_ACCESS_KEY : str = "gemini_storage_user"
    GEMINI_STORAGE_SECRET_KEY : str = "gemini_secret"

    # REST API Configuration
    GEMINI_REST_API_CONTAINER_NAME : str = "geminibase-rest-api"
    GEMINI_REST_API_IMAGE_NAME : str = "geminibase/rest-api"
    GEMINI_REST_API_HOSTNAME : str = "geminibase-rest-api"
    GEMINI_REST_API_PORT : int = 7777
    GEMINI_API_KEY : str = ""
    GEMINI_CORS_ORIGINS : str = "*"

    # Scheduler DB
    GEMINI_SCHEDULER_DB_CONTAINER_NAME : str = "geminibase-scheduler-db"
    GEMINI_SCHEDULER_DB_IMAGE_NAME : str = "geminibase/scheduler-db"
    GEMINI_SCHEDULER_DB_HOSTNAME : str = "geminibase-scheduler-db"
    GEMINI_SCHEDULER_DB_USER: str = "gemini"  # User for scheduler DB
    GEMINI_SCHEDULER_DB_PASSWORD: str = "gemini"
    GEMINI_SCHEDULER_DB_NAME: str = "gemini_scheduler"  # Database name for scheduler
    GEMINI_SCHEDULER_DB_PORT: int = 6432  # Port for scheduler DB

    # Scheduler Server
    GEMINI_SCHEDULER_SERVER_CONTAINER_NAME : str = "geminibase-scheduler-server"
    GEMINI_SCHEDULER_SERVER_IMAGE_NAME : str = "geminibase/scheduler-server"
    GEMINI_SCHEDULER_SERVER_HOSTNAME : str = "geminibase-scheduler-server"
    GEMINI_SCHEDULER_SERVER_PORT : int = 4200

    # TiTiler (tile server for COGs stored in MinIO)
    GEMINI_TITILER_PORT : int = 8091

    # NodeODM (OpenDroneMap processing service)
    GEMINI_NODEODM_PORT : int = 13000

    # UI
    GEMINI_UI_PORT : int = 3000

    # Reverse Proxy
    GEMINI_REVERSE_PROXY_CONTAINER_NAME : str = "geminibase-reverse-proxy"
    GEMINI_REVERSE_PROXY_IMAGE_NAME : str = "geminibase/reverse-proxy"
    GEMINI_REVERSE_PROXY_HOSTNAME : str = "geminibase-reverse-proxy"

    def model_post_init(self, __context: Any) -> None:
        self.apply_type(self.GEMINI_TYPE)
        return super().model_post_init(__context)

    def apply_type(self, gemini_type = "internal"):
        match gemini_type:
            case "public":
                self.set_public_ip(self.GEMINI_PUBLIC_IP)
                # self.set_public_domain(self.GEMINI_PUBLIC_DOMAIN)
            case "local":
                self.set_local()


    def set_debug(self, debug: bool = True):
        os.environ["GEMINI_DEBUG"] = str(debug)

    def set_public_domain(self, domain: str):
        self.__set_hostnames(domain)

    def set_public_ip(self, ip: str):
        self.__set_hostnames(ip)

    def set_local(self):
        self.__set_hostnames("localhost")

    def __set_hostnames(self, hostname: str):
        os.environ["GEMINI_DB_HOSTNAME"] = hostname
        os.environ["GEMINI_LOGGER_HOSTNAME"] = hostname
        os.environ["GEMINI_STORAGE_HOSTNAME"] = hostname
        os.environ["GEMINI_SCHEDULER_DB_HOSTNAME"] = hostname
        os.environ["GEMINI_SCHEDULER_SERVER_HOSTNAME"] = hostname
        os.environ["GEMINI_REST_API_HOSTNAME"] = hostname


    @staticmethod
    def from_env_file(input_env_file_path: str) -> "GEMINISettings":
        if not os.path.exists(input_env_file_path):
            raise FileNotFoundError(f"Environment file {input_env_file_path} not found.")
        config = dotenv_values(input_env_file_path)
        settings = GEMINISettings.model_validate(config)
        return settings
    
    def create_env_file(self, env_file_path: str) -> str:
        dict = self.model_dump()
        with open(env_file_path, 'w') as f:
            for key, value in dict.items():
                f.write(f"{key}={value}\n")
        return env_file_path
    
    def set_setting(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            os.environ[key] = str(value)
            setattr(self, key, value)
        else:
            raise KeyError(f"Setting {key} does not exist in GEMINISettings.")
