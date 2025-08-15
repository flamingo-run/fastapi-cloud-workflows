import asyncio
import json

from app.main import create_app


def test_missing_workflow_name_header():
    app = create_app()

    async def call():
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "path": "/steps/auth-payment",
            "raw_path": b"/steps/auth-payment",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("test", 0),
            "server": ("srv", 80),
            "scheme": "http",
        }

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps({"order_id": "o-1", "price": "1.23"}).encode(),
                "more_body": False,
            }

        captured = {}

        async def send(message):
            if message["type"] == "http.response.start":
                captured["headers"] = {k.decode().title(): v.decode() for k, v in message.get("headers", [])}

        await app(scope, receive, send)
        return captured

    res = asyncio.get_event_loop().run_until_complete(call())
    assert res["headers"].get("X-Workflow-Run-Id")
