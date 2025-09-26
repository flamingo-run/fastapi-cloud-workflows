"""Tests for try/catch functionality."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from fastapi_cloudflow import Context, TryCatchStep, step, try_catch, workflow


# Test models defined at module level to avoid scoping issues
class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int
    error_handled: bool = False


def test_try_catch_builder():
    """Test the try/catch builder pattern."""

    @step(name="main-step")
    async def main_step(ctx: Context, data: InputModel) -> OutputModel:
        if data.value < 0:
            raise ValueError("Negative value not allowed")
        return OutputModel(result=data.value * 2)

    @step(name="error-handler")
    async def error_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=0, error_handled=True)

    # Build try/catch block
    try_block = workflow("try") >> main_step
    except_block = workflow("except") >> error_handler

    tc_builder = try_catch("test-try-catch")
    tc_step = tc_builder.try_block(try_block).except_block(except_block).build()

    assert isinstance(tc_step, TryCatchStep)
    assert tc_step.name == "test-try-catch"
    assert len(tc_step.try_steps) == 1
    assert len(tc_step.except_steps) == 1
    assert tc_step.error_var == "e"
    assert tc_step.raise_on_error is False


def test_try_catch_with_raise():
    """Test try/catch that re-raises after handling."""

    @step(name="risky-step")
    async def risky_step(ctx: Context, data: InputModel) -> OutputModel:
        raise Exception("Something went wrong")

    @step(name="log-error")
    async def log_error(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=-1, error_handled=True)

    try_block = workflow("try") >> risky_step
    except_block = workflow("except") >> log_error

    tc_step = try_catch("with-reraise").try_block(try_block).except_block(except_block).raise_error(True).build()

    assert tc_step.raise_on_error is True


def test_try_catch_without_except():
    """Test try/catch without except block (ignore errors)."""

    @step(name="optional-step")
    async def optional_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    try_block = workflow("try") >> optional_step

    tc_step = try_catch("ignore-errors").try_block(try_block).build()

    assert len(tc_step.except_steps) == 0
    assert tc_step.error_var == "e"


def test_try_catch_custom_error_var():
    """Test try/catch with custom error variable name."""

    @step(name="custom-var-step")
    async def custom_var_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    @step(name="custom-var-handler")
    async def custom_var_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=0, error_handled=True)

    try_block = workflow("try") >> custom_var_step
    except_block = workflow("except") >> custom_var_handler

    tc_step = (
        try_catch("custom-error-var").try_block(try_block).except_block(except_block, error_var="my_error").build()
    )

    assert tc_step.error_var == "my_error"


def test_nested_try_catch():
    """Test nested try/catch blocks."""

    @step(name="inner-step")
    async def inner_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    @step(name="inner-handler")
    async def inner_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=1, error_handled=True)

    @step(name="outer-step")
    async def outer_step(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result + 10)

    @step(name="outer-handler")
    async def outer_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=0, error_handled=True)

    # Inner try/catch
    inner_try = workflow("inner-try") >> inner_step
    inner_except = workflow("inner-except") >> inner_handler
    inner_tc = try_catch("inner-tc").try_block(inner_try).except_block(inner_except).build()

    # Outer try/catch containing the inner one
    outer_try = workflow("outer-try") >> inner_tc >> outer_step
    outer_except = workflow("outer-except") >> outer_handler
    outer_tc = try_catch("outer-tc").try_block(outer_try).except_block(outer_except).build()

    assert isinstance(outer_tc, TryCatchStep)
    assert len(outer_tc.try_steps) == 2  # inner_tc and outer_step
    assert isinstance(outer_tc.try_steps[0], TryCatchStep)


def test_try_catch_in_workflow():
    """Test try/catch as part of a workflow."""

    @step(name="pre-step")
    async def pre_step(ctx: Context, data: InputModel) -> InputModel:
        return InputModel(value=data.value + 1)

    @step(name="risky")
    async def risky(ctx: Context, data: InputModel) -> OutputModel:
        if data.value > 10:
            raise ValueError("Value too large")
        return OutputModel(result=data.value * 2)

    @step(name="fallback")
    async def fallback(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=10, error_handled=True)

    @step(name="post-step")
    async def post_step(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result + 5, error_handled=data.error_handled)

    # Build try/catch
    try_block = workflow("try") >> risky
    except_block = workflow("except") >> fallback
    tc_step = try_catch("safe-risky").try_block(try_block).except_block(except_block).build()

    # Build complete workflow
    wf = (workflow("complete-flow") >> pre_step >> tc_step >> post_step).build()

    assert len(wf.nodes) == 3
    assert isinstance(wf.nodes[1], TryCatchStep)


def test_try_catch_empty_try_block_raises():
    """Test that empty try block raises an error."""

    with pytest.raises(ValueError, match="Try block must contain at least one step"):
        try_catch("empty").build()


def test_try_catch_type_consistency():
    """Test that try/catch maintains type consistency."""

    @step(name="typed-step")
    async def typed_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    @step(name="typed-handler")
    async def typed_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=0, error_handled=True)

    try_block = workflow("try") >> typed_step
    except_block = workflow("except") >> typed_handler

    tc_step = try_catch("typed-tc").try_block(try_block).except_block(except_block).build()

    # Check that input/output models are preserved
    assert tc_step.input_model == InputModel
    assert tc_step.output_model == OutputModel
