import asyncio

from app.flows.order import CreateOrder, OrderDraft, PaymentAuth, auth_payment, price_order
from fastapi_cloudflow.core import Context, WorkflowMeta


def test_step_functions_happy_path():
    ctx = Context(request=None, workflow=WorkflowMeta(name="order-flow", step=None, run_id="run-1"))

    order = CreateOrder(account_id=1, sku="abc", qty=2)

    draft: OrderDraft = asyncio.get_event_loop().run_until_complete(price_order(ctx, order))
    assert draft.order_id.startswith("o-")

    auth: PaymentAuth = asyncio.get_event_loop().run_until_complete(auth_payment(ctx, draft))
    assert auth.order_id == draft.order_id
    assert auth.status == "approved"
