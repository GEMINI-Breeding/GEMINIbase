"""
API key authentication middleware for the GEMINIbase REST API.

When GEMINI_API_KEY is set (non-empty), all requests to /api/* must include
a valid API key via the X-API-Key header or ?api_key query parameter.

Public routes (/, /settings, /schema) are excluded from authentication.
When GEMINI_API_KEY is empty (default), authentication is disabled.
"""

from litestar.middleware import ASGIMiddleware
from litestar.types import Receive, Scope, Send
from litestar.response import Response
from litestar.enums import ScopeType


class APIKeyAuthMiddleware(ASGIMiddleware):
    """Middleware that enforces API key authentication on /api/* routes."""

    scopes = {ScopeType.HTTP}

    def __init__(self, app, api_key: str = "") -> None:
        super().__init__(app)
        self.api_key = api_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.api_key:
            # Auth disabled when no API key is configured
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip auth for non-API routes (root, settings, OpenAPI docs)
        if not path.startswith("/api"):
            await self.app(scope, receive, send)
            return

        # Check X-API-Key header
        headers = dict(scope.get("headers", []))
        header_key = headers.get(b"x-api-key", b"").decode()

        # Check query parameter fallback
        query_string = scope.get("query_string", b"").decode()
        query_key = ""
        for param in query_string.split("&"):
            if param.startswith("api_key="):
                query_key = param.split("=", 1)[1]
                break

        if header_key == self.api_key or query_key == self.api_key:
            await self.app(scope, receive, send)
            return

        # Reject with 401
        response = Response(
            content={"error": "Invalid or missing API key. Provide via X-API-Key header."},
            status_code=401,
            media_type="application/json",
        )
        await response(scope, receive, send)


def create_api_key_middleware(api_key: str):
    """Factory that returns a middleware class pre-configured with the API key."""
    if not api_key:
        return None

    def middleware_factory(app):
        return APIKeyAuthMiddleware(app, api_key=api_key)

    middleware_factory.__name__ = "APIKeyAuthMiddleware"
    return middleware_factory
