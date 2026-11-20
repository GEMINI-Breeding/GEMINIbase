"""
API key authentication middleware for the GEMINIbase REST API.

When GEMINI_API_KEY is set (non-empty), all requests to /api/* must include
a valid API key via the X-API-Key header or ?api_key query parameter.

Public routes (/, /settings, /schema) are excluded from authentication.
When GEMINI_API_KEY is empty (default), authentication is disabled.
"""

from litestar.types import ASGIApp, Receive, Scope, Send
from litestar.enums import ScopeType


class APIKeyAuthMiddleware:
    """Middleware that enforces API key authentication on /api/* routes.

    A plain ASGI wrapper (an app in, an app out), which every Litestar 2.x
    accepts as middleware. It used to subclass ``ASGIMiddleware``, whose
    newer releases make ``handle`` abstract: setting GEMINI_API_KEY then
    stopped the API from starting.
    """

    def __init__(self, app: ASGIApp, api_key: str = "") -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.api_key or scope.get("type") != ScopeType.HTTP:
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

        # Reject with 401 (sent as plain ASGI messages: a Litestar Response
        # is not itself an ASGI app outside a route handler).
        body = b'{"error": "Invalid or missing API key. Provide via X-API-Key header."}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})


def create_api_key_middleware(api_key: str):
    """Factory that returns a middleware class pre-configured with the API key."""
    if not api_key:
        return None

    def middleware_factory(app):
        return APIKeyAuthMiddleware(app, api_key=api_key)

    middleware_factory.__name__ = "APIKeyAuthMiddleware"
    return middleware_factory
