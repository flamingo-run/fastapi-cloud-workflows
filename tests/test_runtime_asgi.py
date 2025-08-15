import asyncio
import json

from app.main import create_app


async def _asgi_call(app, path: str, body: dict, headers: dict[str, str]):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
    }

    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.request", "body": b"", "more_body": False}
        received = True
        return {"type": "http.request", "body": json.dumps(body).encode(), "more_body": False}

    result = {"status": None, "headers": {}, "body": b""}

    async def send(message):
        if message["type"] == "http.response.start":
            result["status"] = message["status"]
            hdrs = {}
            for k, v in message.get("headers", []):
                hdrs[k.decode().title()] = v.decode()
            result["headers"] = hdrs
        elif message["type"] == "http.response.body":
            result["body"] += message.get("body", b"")

    await app(scope, receive, send)
    return result


def test_asgi_pipeline_with_middleware_and_handler():
    app = create_app()
    res = asyncio.get_event_loop().run_until_complete(
        _asgi_call(
            app,
            "/steps/price-order",
            body={"account_id": 1, "sku": "abc", "qty": 2},
            headers={
                "X-Workflow-Run-Id": "run-123",
                "X-Workflow-Name": "order-flow",
                "Content-Type": "application/json",
            },
        )
    )
    assert res["status"] == 200
    assert res["headers"].get("X-Workflow-Run-Id") == "run-123"
    data = json.loads(res["body"].decode())
    assert set(data.keys()) == {"order_id", "price"}
