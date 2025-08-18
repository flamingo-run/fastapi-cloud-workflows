from __future__ import annotations

from fastapi.testclient import TestClient
from main import app


def test_price_order() -> None:
    c = TestClient(app)
    r = c.post(
        "/steps/price-order",
        headers={"X-Workflow-Name": "unit"},
        json={"account_id": 1, "sku": "abc", "qty": 1},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["order_id"].startswith("o-")
    assert "price" in body


def test_auth_payment() -> None:
    c = TestClient(app)
    draft = {"order_id": "o-test", "price": "12.34"}
    r = c.post(
        "/steps/auth-payment",
        headers={"X-Workflow-Name": "unit", "X-Workflow-Run-Id": "test"},
        json=draft,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["order_id"].startswith("o-")
    assert body["status"] == "approved"
