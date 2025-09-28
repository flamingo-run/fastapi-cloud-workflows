"""Retry-focused workflow example used for documentation and contract tests."""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel

from fastapi_cloudflow import Context, HttpStep, RetryPolicy, step, workflow


class RetryInput(BaseModel):
    value: int


class RetryResult(BaseModel):
    result: int


@step(
    name="retry-entry",
    retry=RetryPolicy(
        max_retries=3,
        initial_delay_s=2.0,
        max_delay_s=10.0,
        multiplier=2.0,
        predicate="http.default_retry_predicate",
    ),
    timeout=timedelta(seconds=30),
)
async def retry_entry(ctx: Context, data: RetryInput) -> RetryInput:
    return RetryInput(value=data.value + 1)


PAYMENT_GATEWAY = HttpStep(
    name="retry-gateway",
    input_model=RetryInput,
    output_model=RetryResult,
    method="POST",
    url="https://api.example.com/payments",
    retry=RetryPolicy.idempotent_http(),
    timeout=timedelta(seconds=60),
)


@step(name="retry-finalize")
async def retry_finalize(ctx: Context, data: RetryResult) -> RetryResult:
    return RetryResult(result=data.result)


def build_retry_demo_workflow():
    """Create a workflow showcasing HTTP and step-level retry policies."""

    return (workflow("retry-demo") >> retry_entry >> PAYMENT_GATEWAY >> retry_finalize).build()


RETRY_DEMO_WORKFLOW = build_retry_demo_workflow()
