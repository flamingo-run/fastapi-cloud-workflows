"""Tests for step.py core module to improve coverage."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from pydantic import BaseModel

from fastapi_cloudflow import Context, HttpStep, ModelAdapter, RetryPolicy, Step
from fastapi_cloudflow.core.step import AssignStep


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


class RequestModel(BaseModel):
    data: str


class ResponseModel(BaseModel):
    response: str


def test_step_call_without_function():
    """Test that calling a Step without a function raises RuntimeError."""
    # Create a step without a function (like HttpStep or AssignStep)
    native_step = Step("native-step", InputModel, OutputModel, fn=None)

    ctx = Context(request=None, workflow=None)  # type: ignore
    data = InputModel(value=42)

    with pytest.raises(RuntimeError, match="Step is not callable. Is it a native step?"):
        asyncio.run(native_step(ctx, data))


def test_http_step_is_not_callable():
    """Test that HttpStep (which has no fn) raises RuntimeError when called."""
    http_step = HttpStep(
        name="http-step",
        input_model=RequestModel,
        output_model=ResponseModel,
        method="POST",
        url="https://api.example.com/endpoint",
    )

    ctx = Context(request=None, workflow=None)  # type: ignore
    data = RequestModel(data="test")

    with pytest.raises(RuntimeError, match="Step is not callable. Is it a native step?"):
        asyncio.run(http_step(ctx, data))


def test_assign_step_is_not_callable():
    """Test that AssignStep (which has no fn) raises RuntimeError when called."""
    assign_step = AssignStep(
        name="assign-step", input_model=InputModel, output_model=OutputModel, expr={"result": "${payload.value * 2}"}
    )

    ctx = Context(request=None, workflow=None)  # type: ignore
    data = InputModel(value=42)

    with pytest.raises(RuntimeError, match="Step is not callable. Is it a native step?"):
        asyncio.run(assign_step(ctx, data))


def test_model_adapter_initialization():
    """Test ModelAdapter initialization and attributes."""
    mapping = {"result": "${payload.value}", "extra": "${payload.value * 2}"}

    adapter = ModelAdapter(name="adapter-step", input_model=InputModel, output_model=OutputModel, mapping=mapping)

    assert adapter.name == "adapter-step"
    assert adapter.input_model == InputModel
    assert adapter.output_model == OutputModel
    assert adapter.mapping == mapping
    assert adapter.fn is None  # ModelAdapter has no function


def test_model_adapter_with_complex_mapping():
    """Test ModelAdapter with complex mapping expressions."""

    class ComplexInput(BaseModel):
        first_name: str
        last_name: str
        age: int

    class ComplexOutput(BaseModel):
        full_name: str
        is_adult: bool
        age_in_months: int

    adapter = ModelAdapter(
        name="complex-adapter",
        input_model=ComplexInput,
        output_model=ComplexOutput,
        mapping={
            "full_name": '${payload.first_name + " " + payload.last_name}',
            "is_adult": "${payload.age >= 18}",
            "age_in_months": "${payload.age * 12}",
        },
    )

    assert adapter.name == "complex-adapter"
    assert len(adapter.mapping) == 3
    assert adapter.input_model == ComplexInput
    assert adapter.output_model == ComplexOutput


def test_model_adapter_is_not_callable():
    """Test that ModelAdapter raises RuntimeError when called."""
    adapter = ModelAdapter(
        name="test-adapter", input_model=InputModel, output_model=OutputModel, mapping={"result": "${payload.value}"}
    )

    ctx = Context(request=None, workflow=None)  # type: ignore
    data = InputModel(value=42)

    with pytest.raises(RuntimeError, match="Step is not callable. Is it a native step?"):
        asyncio.run(adapter(ctx, data))


def test_step_with_tags():
    """Test Step initialization with tags."""
    tags = ["important", "validation", "experimental"]

    async def dummy_fn(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    step = Step(name="tagged-step", input_model=InputModel, output_model=OutputModel, fn=dummy_fn, tags=tags)

    assert step.tags == {"important", "validation", "experimental"}
    assert isinstance(step.tags, set)


def test_http_step_with_all_options():
    """Test HttpStep with all configuration options."""
    from fastapi_cloudflow import Arg

    headers = {"X-Custom-Header": "value", "X-Dynamic": Arg.env("DYNAMIC_HEADER")}

    auth = {"type": "OIDC", "audience": Arg.env("API_AUDIENCE")}

    http_step = HttpStep(
        name="full-http-step",
        input_model=RequestModel,
        output_model=ResponseModel,
        method="PUT",
        url=Arg.env("API_URL") / "endpoint",
        headers=headers,
        auth=auth,
        retry=RetryPolicy(max_retries=5),
        timeout=timedelta(seconds=60),
    )

    assert http_step.name == "full-http-step"
    assert http_step.method == "PUT"
    assert http_step.headers == headers
    assert http_step.auth == auth
    assert http_step.retry is not None
    assert http_step.retry.max_retries == 5
    assert http_step.timeout == timedelta(seconds=60)


def test_assign_step_expr():
    """Test AssignStep stores expressions correctly."""
    expr = {"field1": "${payload.value}", "field2": "${payload.value * 2}", "field3": "static_value"}

    assign_step = AssignStep(name="assignment", input_model=InputModel, output_model=OutputModel, expr=expr)

    assert assign_step.expr == expr
    assert assign_step.name == "assignment"
