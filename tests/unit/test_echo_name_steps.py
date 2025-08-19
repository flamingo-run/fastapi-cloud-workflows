from __future__ import annotations

from fastapi.testclient import TestClient
from main import app


def test_extract_name_and_name_shout() -> None:
    c = TestClient(app)

    # extract-name expects the httpbin response shape: {"json": {...}}
    r1 = c.post(
        "/steps/extract-name",
        headers={"X-Workflow-Name": "unit"},
        json={"json": {"name": "Ada Lovelace"}},
    )
    assert r1.status_code == 200
    extracted = r1.json()
    assert extracted["echoed_name"] == "Ada Lovelace"

    # name-shout expects EchoOut
    r2 = c.post(
        "/steps/name-shout",
        headers={"X-Workflow-Name": "unit", "X-Workflow-Run-Id": "test"},
        json=extracted,
    )
    assert r2.status_code == 200
    shouted = r2.json()
    assert shouted["name_upper"] == "ADA LOVELACE"
    assert shouted["length"] == len("ADA LOVELACE")
