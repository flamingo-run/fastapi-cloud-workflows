from __future__ import annotations

from fastapi.testclient import TestClient
from main import app


def test_malformed_json_returns_422() -> None:
    c = TestClient(app)
    r = c.post(
        "/steps/price-order",
        headers={"X-Workflow-Name": "unit", "Content-Type": "application/json"},
        data="{not-json}",
    )
    assert r.status_code == 422
    assert "Malformed JSON" in r.text


def test_missing_body_returns_422() -> None:
    c = TestClient(app)
    r = c.post("/steps/price-order", headers={"X-Workflow-Name": "unit"})
    assert r.status_code == 422
    assert ("Request body required" in r.text) or ("Malformed JSON body" in r.text)


def test_payload_wrapper_is_accepted() -> None:
    c = TestClient(app)
    wrapped = {"payload": {"account_id": 1, "sku": "abc", "qty": 1}}
    r = c.post("/steps/price-order", headers={"X-Workflow-Name": "unit"}, json=wrapped)
    assert r.status_code == 200


def test_validation_error_returns_422() -> None:
    c = TestClient(app)
    # Missing required fields
    r = c.post("/steps/price-order", headers={"X-Workflow-Name": "unit"}, json={})
    assert r.status_code == 422
