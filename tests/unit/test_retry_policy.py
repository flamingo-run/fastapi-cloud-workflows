"""Tests for retry policy functionality."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_cloudflow import Context, RetryPolicy, step, workflow
from fastapi_cloudflow.runtime import build_app

if TYPE_CHECKING:
    pass


# Test models defined at module level to avoid scoping issues
class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


class RequestModel(BaseModel):
    data: str


class ResponseModel(BaseModel):
    result: str


class DataModel(BaseModel):
    value: int


def test_retry_policy_creation():
    """Test creating retry policies."""
    policy = RetryPolicy(
        max_retries=3,
        initial_delay_s=1.0,
        max_delay_s=10.0,
        multiplier=2.0,
        predicate="http.default_retry_predicate",
    )

    assert policy.max_retries == 3
    assert policy.initial_delay_s == 1.0
    assert policy.max_delay_s == 10.0
    assert policy.multiplier == 2.0
    assert policy.predicate == "http.default_retry_predicate"


def test_idempotent_http_retry_policy():
    """Test the idempotent HTTP retry policy factory."""
    policy = RetryPolicy.idempotent_http()

    assert policy.max_retries == 5
    assert policy.initial_delay_s == 1.0
    assert policy.max_delay_s == 30.0
    assert policy.multiplier == 2.0
    assert policy.predicate == "http.default_retry_predicate"


def test_step_with_retry_policy():
    """Test that steps can be created with retry policies."""

    @step(name="retryable-step", retry=RetryPolicy(max_retries=3), timeout=timedelta(seconds=30))
    async def retryable_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    assert retryable_step.retry is not None
    assert retryable_step.retry.max_retries == 3
    assert retryable_step.timeout == timedelta(seconds=30)


def test_http_step_with_retry():
    """Test HTTP steps with retry policies."""
    from fastapi_cloudflow import HttpStep

    http_step = HttpStep(
        name="http-with-retry",
        input_model=RequestModel,
        output_model=ResponseModel,
        method="POST",
        url="https://api.example.com/endpoint",
        retry=RetryPolicy.idempotent_http(),
        timeout=timedelta(seconds=60),
    )

    assert http_step.retry is not None
    assert http_step.retry.max_retries == 5
    assert http_step.timeout == timedelta(seconds=60)


def test_workflow_with_retryable_steps():
    """Test building workflows with retryable steps."""

    @step(name="step1", retry=RetryPolicy(max_retries=2))
    async def step1(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value + 1)

    @step(name="step2", retry=RetryPolicy(max_retries=3))
    async def step2(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result * 2)

    wf = (workflow("retry-workflow") >> step1 >> step2).build()

    assert len(wf.nodes) == 2
    assert wf.nodes[0].retry.max_retries == 2
    assert wf.nodes[1].retry.max_retries == 3


def test_step_endpoint_with_retry():
    """Test that step endpoints work correctly with retry policies."""

    @step(name="test-retry-step", retry=RetryPolicy(max_retries=3))
    async def test_retry_step(ctx: Context, data: DataModel) -> DataModel:
        return DataModel(value=data.value * 2)

    # Build app and test
    app = build_app()
    client = TestClient(app)

    # Import to register the step
    _ = (workflow("test-wf") >> test_retry_step).build()

    # Rebuild app to include registered steps
    app = build_app()
    client = TestClient(app)

    response = client.post("/steps/test-retry-step", headers={"X-Workflow-Name": "test"}, json={"value": 5})

    assert response.status_code == 200
    assert response.json() == {"value": 10}
