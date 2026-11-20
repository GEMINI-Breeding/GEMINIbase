"""The API key middleware (gemini.rest_api.auth): a missing or wrong key is a 401, not a crash."""
import asyncio

from gemini.rest_api.auth import create_api_key_middleware


def _call(path, headers=(), query=b""):
    sent = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request", "body": b""}

    mw = create_api_key_middleware("s3cret")(app)
    scope = {"type": "http", "path": path, "headers": list(headers), "query_string": query}
    asyncio.run(mw(scope, receive, send))
    return sent[0]["status"]


def test_no_key_configured_means_no_middleware():
    assert create_api_key_middleware("") is None


def test_api_routes_need_the_key():
    assert _call("/api/x") == 401
    assert _call("/api/x", headers=[(b"x-api-key", b"wrong")]) == 401
    assert _call("/api/x", headers=[(b"x-api-key", b"s3cret")]) == 200
    assert _call("/api/x", query=b"api_key=s3cret") == 200


def test_public_routes_stay_open():
    assert _call("/") == 200
    assert _call("/schema") == 200
