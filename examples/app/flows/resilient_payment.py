"""Example workflow demonstrating retry and try/catch features."""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel

from fastapi_cloudflow import (
    Arg,
    Context,
    HttpStep,
    RetryPolicy,
    TryCatchStep,
    step,
    workflow,
)


class PaymentRequest(BaseModel):
    amount: float
    currency: str
    customer_id: str
    retry_count: int = 0


class PaymentResult(BaseModel):
    transaction_id: str | None
    status: str
    error: str | None = None
    retry_count: int = 0


class FallbackResult(BaseModel):
    fallback_used: bool
    original_error: str | None
    status: str


# Step with retry policy for flaky payment provider
@step(
    name="process-payment",
    retry=RetryPolicy(
        max_retries=3,
        initial_delay_s=2.0,
        max_delay_s=10.0,
        multiplier=2.0,
        predicate="http.default_retry_predicate",
    ),
    timeout=timedelta(seconds=30),
)
async def process_payment(ctx: Context, data: PaymentRequest) -> PaymentResult:
    """Process payment with automatic retries on failure."""
    # In real implementation, this would call an actual payment service
    # For demo purposes, we'll simulate potential failures
    import random

    # Simulate 30% failure rate for demo
    if random.random() < 0.3:
        raise Exception("Payment processing temporarily unavailable")

    return PaymentResult(
        transaction_id=f"txn_{data.customer_id}_{data.amount}", status="success", retry_count=data.retry_count
    )


# HTTP step with retry for external payment gateway
payment_gateway = HttpStep(
    name="payment-gateway",
    input_model=PaymentRequest,
    output_model=PaymentResult,
    method="POST",
    url=Arg.env("PAYMENT_GATEWAY_URL") / "charge",
    retry=RetryPolicy(
        max_retries=5,
        initial_delay_s=1.0,
        max_delay_s=30.0,
        multiplier=1.5,
        predicate="http.default_retry_predicate",
    ),
    timeout=timedelta(seconds=60),
    auth={"type": "OIDC", "audience": Arg.env("PAYMENT_GATEWAY_URL")},
)


@step(name="fallback-payment")
async def fallback_payment(ctx: Context, data: PaymentRequest) -> FallbackResult:
    """Fallback payment processor when primary fails."""
    # This would use an alternative payment method
    return FallbackResult(fallback_used=True, original_error="Primary payment failed", status="processed_via_fallback")


@step(name="log-failure")
async def log_failure(ctx: Context, data: PaymentRequest) -> PaymentResult:
    """Log payment failure for audit."""
    return PaymentResult(
        transaction_id=None, status="failed", error="Payment could not be processed", retry_count=data.retry_count + 1
    )


# Build a workflow with try/catch for resilient payment processing
def build_resilient_payment_workflow():
    """Create a payment workflow with error handling and retries."""

    # Try to process payment with primary provider
    try_primary = workflow("primary-payment") >> process_payment

    # Fallback flow if primary fails
    fallback_flow = workflow("fallback-flow") >> fallback_payment

    # Create try/catch block
    payment_with_fallback = TryCatchStep(
        name="payment-with-fallback",
        input_model=PaymentRequest,
        output_model=PaymentResult,  # Changed to match the actual output
        try_steps=try_primary.nodes,
        except_steps=[fallback_payment, log_failure],  # Use actual step instances
        error_var="payment_error",
        raise_on_error=False,  # Don't re-raise, we handled it
    )

    # Build the complete workflow
    return (workflow("resilient-payment-flow") >> payment_with_fallback).build()


# Alternative approach using HTTP gateway with try/catch
def build_gateway_payment_workflow():
    """Create a workflow using external gateway with error handling."""

    # Try external gateway
    gateway_flow = workflow("gateway-payment") >> payment_gateway

    # Build try/catch with fallback
    gateway_with_fallback = TryCatchStep(
        name="gateway-with-fallback",
        input_model=PaymentRequest,
        output_model=PaymentResult,  # Ensure consistent output model
        try_steps=gateway_flow.nodes,
        except_steps=[fallback_payment, log_failure],  # Fallback steps
        error_var="gateway_error",
        raise_on_error=False,
    )

    return (workflow("gateway-payment-flow") >> gateway_with_fallback).build()


# Export workflows
RESILIENT_PAYMENT_FLOW = build_resilient_payment_workflow()
GATEWAY_PAYMENT_FLOW = build_gateway_payment_workflow()
