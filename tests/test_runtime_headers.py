import asyncio
import json

from app.main import create_app


async def _call(app):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/steps/price-order",
        "raw_path": b"/steps/price-order",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("test", 0),
        "server": ("srv", 80),
        "scheme": "http",
    }
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {
            "type": "http.request",
            "body": json.dumps({"account_id": 1, "sku": "a", "qty": 1}).encode(),
            "more_body": False,
        }

    result = {}

    async def send(message):
        if message["type"] == "http.response.start":
            headers = {k.decode().title(): v.decode() for k, v in message.get("headers", [])}
            result["headers"] = headers
        elif message["type"] == "http.response.body":
            result["status"] = 200

    await app(scope, receive, send)
    return result


def test_middleware_generates_run_id_when_absent():
    app = create_app()
    res = asyncio.get_event_loop().run_until_complete(_call(app))
    assert res["headers"].get("X-Workflow-Run-Id")
