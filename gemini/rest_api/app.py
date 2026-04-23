from litestar import Litestar, Router, get, Response
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import StoplightRenderPlugin
from litestar.config.cors import CORSConfig
from gemini.rest_api.controllers import controllers
from gemini.rest_api.auth import create_api_key_middleware
from gemini.rest_api.infrastructure import (
    database_health,
    exception_handlers as infra_exception_handlers,
    infrastructure_gate,
)
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
    title="GEMINIbase REST API",
    version="1.0.0",
    description="REST API for GEMINIbase",
    render_plugins=[StoplightRenderPlugin()]
)

@get(path="/" , sync_to_thread=False, tags=["GEMINIbase"])
def root_handler() -> dict:
    return {
        "message": "Welcome to the GEMINIbase API",
        "author": "Pranav Ghate",
        "version": "1.0.0",
        "email": "pghate@ucdavis.edu"
    }

@get(path="/settings", sync_to_thread=False, tags=["GEMINIbase"])
def settings_handler() -> dict:
    return GEMINISettings().model_dump()

@get(path="/healthz", sync_to_thread=True, tags=["GEMINIbase"])
def healthz_handler() -> Response:
    """Liveness + readiness probe. 200 when all infra components are reachable,
    503 otherwise — the compose healthcheck hits this path."""
    status = database_health.status()
    payload = {
        "status": "ok" if status.healthy else "degraded",
        "database": {
            "healthy": status.healthy,
            "detail": status.detail,
        },
    }
    return Response(content=payload, status_code=200 if status.healthy else 503)

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
    route_handlers=[root_handler, settings_handler, healthz_handler] + routers,
    openapi_config=openapi_config,
    cors_config=cors_config,
    middleware=middleware,
    before_request=infrastructure_gate,
    exception_handlers=infra_exception_handlers,
)
