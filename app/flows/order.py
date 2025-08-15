from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel

from fastapi_cloudflow import Context, step, workflow


class CreateOrder(BaseModel):
    account_id: int
    sku: str
    qty: int


class OrderDraft(BaseModel):
    order_id: str
    price: Decimal


class PaymentAuth(BaseModel):
    order_id: str
    status: str


@step(name="price-order")
async def price_order(ctx: Context, data: CreateOrder) -> OrderDraft:
    return OrderDraft(order_id=f"o-{uuid4().hex}", price=Decimal("12.34"))


@step(name="auth-payment")
async def auth_payment(ctx: Context, data: OrderDraft) -> PaymentAuth:
    return PaymentAuth(order_id=data.order_id, status="approved")


# Building the workflow auto-registers it in the registry
ORDER_FLOW = (workflow("order-flow") >> price_order >> auth_payment).build()
