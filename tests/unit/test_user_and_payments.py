from __future__ import annotations

from fastapi.testclient import TestClient
from main import app


def test_hash_password() -> None:
    c = TestClient(app)
    r = c.post(
        "/steps/hash-password",
        headers={"X-Workflow-Name": "unit"},
        json={"email": "user@example.com", "password": "hunter2asdf"},
    )
    assert r.status_code == 200
    draft = r.json()
    assert draft["hashed_password"].startswith("hashed:")


def test_validate_cart_and_summarize() -> None:
    c = TestClient(app)
    r1 = c.post(
        "/steps/validate-cart",
        headers={"X-Workflow-Name": "unit"},
        json={"total": 10.0, "currency": "USD"},
    )
    assert r1.status_code == 200
    r2 = c.post(
        "/steps/summarize-charge",
        headers={"X-Workflow-Name": "unit", "X-Workflow-Run-Id": "test"},
        json={"status": "approved", "psp_id": "p-1"},
    )
    assert r2.status_code == 200
    res = r2.json()
    assert res["ok"] is True
    assert res["txn_id"] == "p-1"
