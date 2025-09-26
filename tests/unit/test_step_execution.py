"""Tests for step execution to improve coverage."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from fastapi_cloudflow import Context, Step
from fastapi_cloudflow.core.types import WorkflowMeta


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


def test_step_successful_execution():
    """Test that a Step with a function executes successfully."""

    async def test_function(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    step = Step(name="test-step", input_model=InputModel, output_model=OutputModel, fn=test_function)

    # Create a context
    ctx = Context(
        request=None,  # type: ignore
        workflow=WorkflowMeta(name="test", step="test-step"),
    )
    data = InputModel(value=21)

    # Execute the step - this covers line 43 in step.py
    result = asyncio.run(step(ctx, data))

    assert isinstance(result, OutputModel)
    assert result.result == 42


def test_step_with_complex_logic():
    """Test step execution with more complex logic."""

    async def complex_step(ctx: Context, data: InputModel) -> OutputModel:
        # Access context information
        assert ctx.workflow.name == "complex-test"
        assert ctx.workflow.step == "complex-step"

        # Perform calculation
        result = abs(data.value) * 3 if data.value < 0 else data.value * 2

        return OutputModel(result=result)

    step = Step(name="complex-step", input_model=InputModel, output_model=OutputModel, fn=complex_step)

    ctx = Context(
        request=None,  # type: ignore
        workflow=WorkflowMeta(name="complex-test", step="complex-step"),
    )

    # Test with positive value
    data_positive = InputModel(value=10)
    result_positive = asyncio.run(step(ctx, data_positive))
    assert result_positive.result == 20

    # Test with negative value
    data_negative = InputModel(value=-10)
    result_negative = asyncio.run(step(ctx, data_negative))
    assert result_negative.result == 30


def test_step_accessing_context():
    """Test that steps can access and use context information."""

    async def context_aware_step(ctx: Context, data: InputModel) -> OutputModel:
        # Use context information in the step logic
        multiplier = 3 if ctx.workflow.run_id else 2

        return OutputModel(result=data.value * multiplier)

    step = Step(name="context-step", input_model=InputModel, output_model=OutputModel, fn=context_aware_step)

    # Test without run_id
    ctx_without_id = Context(
        request=None,  # type: ignore
        workflow=WorkflowMeta(name="test", step="context-step", run_id=None),
    )
    data = InputModel(value=5)
    result_without_id = asyncio.run(step(ctx_without_id, data))
    assert result_without_id.result == 10

    # Test with run_id
    ctx_with_id = Context(
        request=None,  # type: ignore
        workflow=WorkflowMeta(name="test", step="context-step", run_id="test-run-123"),
    )
    result_with_id = asyncio.run(step(ctx_with_id, data))
    assert result_with_id.result == 15
