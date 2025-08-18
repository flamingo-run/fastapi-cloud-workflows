from __future__ import annotations

from fastapi.testclient import TestClient
from main import app


def test_joke_split_and_rate() -> None:
    c = TestClient(app)

    # Manually simulate the payload of joke-fetch output
    fake = {
        "id": "abc",
        "joke": "Why did the chicken cross the road? To get to the other side!",
        "status": 200,
    }

    r1 = c.post(
        "/steps/joke-split",
        headers={"X-Workflow-Name": "unit"},
        json=fake,
    )
    assert r1.status_code == 200
    bits = r1.json()
    assert "setup" in bits and "punch" in bits

    r2 = c.post(
        "/steps/joke-rate",
        headers={"X-Workflow-Name": "unit", "X-Workflow-Run-Id": "test"},
        json=bits,
    )
    assert r2.status_code == 200
    rated = r2.json()
    assert isinstance(rated.get("rating"), int)
