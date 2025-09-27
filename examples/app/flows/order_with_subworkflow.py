"""Order processing with payment as a subworkflow."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, step, workflow


# Payment workflow models and steps
class PaymentRequest(BaseModel):
    amount: float
    customer_id: str
    payment_method: str


class PaymentResult(BaseModel):
    transaction_id: str
    status: str
    amount: float


@step(name="validate-payment")
async def validate_payment(ctx: Context, data: PaymentRequest) -> PaymentRequest:
    """Validate payment details."""
    if data.amount <= 0:
        raise ValueError("Invalid payment amount")
    return data


@step(name="charge-card")
async def charge_card(ctx: Context, data: PaymentRequest) -> PaymentResult:
    """Process the payment."""
    return PaymentResult(transaction_id=f"txn_{data.customer_id}_{data.amount}", status="success", amount=data.amount)


# Build the payment workflow
PAYMENT_WORKFLOW = (workflow("payment-processing") >> validate_payment >> charge_card).build()


# Order workflow models and steps
class OrderRequest(BaseModel):
    order_id: str
    customer_id: str
    items: list[str]
    total_amount: float


class OrderValidated(BaseModel):
    order_id: str
    customer_id: str
    amount: float
    payment_method: str


class OrderComplete(BaseModel):
    order_id: str
    transaction_id: str
    status: str


@step(name="validate-order")
async def validate_order(ctx: Context, data: OrderRequest) -> PaymentRequest:
    """Validate the order and prepare payment request."""
    return PaymentRequest(amount=data.total_amount, customer_id=data.customer_id, payment_method="credit_card")


@step(name="ship-order")
async def ship_order(ctx: Context, data: PaymentResult) -> OrderComplete:
    """Ship the order after successful payment."""
    return OrderComplete(
        order_id="order_123",  # Would normally come from context
        transaction_id=data.transaction_id,
        status="shipped",
    )


# Build the order workflow using payment as a subworkflow
ORDER_WORKFLOW = (
    workflow("order-processing")
    >> validate_order
    >> PAYMENT_WORKFLOW  # Use payment workflow as a subworkflow
    >> ship_order
).build()
