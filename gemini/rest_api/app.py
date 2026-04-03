from litestar import Litestar, Router, get
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import StoplightRenderPlugin
from litestar.config.cors import CORSConfig
from gemini.rest_api.controllers import controllers
from gemini.rest_api.auth import create_api_key_middleware
from gemini.config.settings import GEMINISettings

settings = GEMINISettings()

# CORS: configurable via GEMINI_CORS_ORIGINS (comma-separated list or "*")
cors_origins_raw = settings.GEMINI_CORS_ORIGINS.strip()
if cors_origins_raw == "*":
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
cors_config = CORSConfig(allow_origins=cors_origins)

# API key auth: enabled when GEMINI_API_KEY is set to a non-empty value
middleware = []
api_key_middleware = create_api_key_middleware(settings.GEMINI_API_KEY)
if api_key_middleware:
    middleware.append(api_key_middleware)

openapi_config = OpenAPIConfig(
    title="GEMINI REST API",
    version="1.0.0",
    description="REST API for the GEMINI project",
    render_plugins=[StoplightRenderPlugin()]
)

@get(path="/" , sync_to_thread=False, tags=["GEMINI"])
def root_handler() -> dict:
    return {
        "message": "Welcome to the GEMINI API",
        "author": "Pranav Ghate",
        "version": "1.0.0",
        "email": "pghate@ucdavis.edu"
    }

@get(path="/settings", sync_to_thread=False, tags=["GEMINI"])
def settings_handler() -> dict:
    return GEMINISettings().model_dump()

routers = []
for key, value in controllers.items():
    router = Router(
        path=f"/api/{key}",
        route_handlers=[value],
        tags=[key.replace("_", " ").title()]
    )
    routers.append(router)


# Entry point for the application
app = Litestar(
    route_handlers=[root_handler, settings_handler] + routers,
    openapi_config=openapi_config,
    cors_config=cors_config,
    middleware=middleware,
)
