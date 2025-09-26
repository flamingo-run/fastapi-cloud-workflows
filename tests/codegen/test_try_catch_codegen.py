"""Tests for try/catch YAML code generation."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from pydantic import BaseModel

from fastapi_cloudflow import Context, step, try_catch, workflow
from fastapi_cloudflow.codegen.workflows import emit_workflow_yaml, workflow_to_yaml_dict


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


def test_try_catch_yaml_emission():
    """Test that try/catch blocks are correctly emitted in YAML."""

    @step(name="try-step")
    async def try_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    @step(name="except-step")
    async def except_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=0)

    # Build try/catch
    try_block = workflow("try") >> try_step
    except_block = workflow("except") >> except_step

    tc_step = try_catch("test-tc").try_block(try_block).except_block(except_block).build()

    wf = (workflow("tc-test-flow") >> tc_step).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    # Check main structure
    assert "main" in yaml_dict
    assert "steps" in yaml_dict["main"]

    # Find the try/catch step
    steps = yaml_dict["main"]["steps"]
    tc_yaml = next((s for s in steps if "try_catch_test-tc" in s), None)
    assert tc_yaml is not None

    tc_def = tc_yaml["try_catch_test-tc"]
    assert "try" in tc_def
    assert "except" in tc_def

    # Check try block
    assert "steps" in tc_def["try"]
    try_steps = tc_def["try"]["steps"]
    assert len(try_steps) > 0

    # Check except block
    assert "as" in tc_def["except"]
    assert tc_def["except"]["as"] == "e"
    assert "steps" in tc_def["except"]
    except_steps = tc_def["except"]["steps"]
    assert len(except_steps) > 0


def test_try_catch_with_reraise():
    """Test try/catch with re-raise after handling."""

    @step(name="reraise-risky")
    async def reraise_risky(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    @step(name="reraise-handler")
    async def reraise_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=-1)

    try_block = workflow("try") >> reraise_risky
    except_block = workflow("except") >> reraise_handler

    tc_step = try_catch("tc-reraise").try_block(try_block).except_block(except_block).raise_error(True).build()

    wf = (workflow("reraise-flow") >> tc_step).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]
    tc_yaml = next((s for s in steps if "try_catch_tc-reraise" in s), None)
    assert tc_yaml is not None
    tc_def = tc_yaml["try_catch_tc-reraise"]

    # Check for reraise step in except block
    except_steps = tc_def["except"]["steps"]
    reraise_step = next((s for s in except_steps if "reraise_tc-reraise" in s), None)
    assert reraise_step is not None
    assert "raise" in reraise_step["reraise_tc-reraise"]
    assert reraise_step["reraise_tc-reraise"]["raise"] == "${e}"


def test_try_catch_custom_error_var():
    """Test try/catch with custom error variable."""

    @step(name="custom-step1")
    async def custom_step1(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    @step(name="custom-error-handler")
    async def custom_error_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=0)

    try_block = workflow("try") >> custom_step1
    except_block = workflow("except") >> custom_error_handler

    tc_step = try_catch("custom-var-tc").try_block(try_block).except_block(except_block, error_var="my_error").build()

    wf = (workflow("custom-var-flow") >> tc_step).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]
    tc_yaml = next((s for s in steps if "try_catch_custom-var-tc" in s), None)
    assert tc_yaml is not None
    tc_def = tc_yaml["try_catch_custom-var-tc"]

    assert tc_def["except"]["as"] == "my_error"


def test_nested_try_catch():
    """Test nested try/catch blocks in YAML."""

    @step(name="nested-inner-step")
    async def nested_inner_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    @step(name="nested-inner-handler")
    async def nested_inner_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=1)

    @step(name="nested-outer-step")
    async def nested_outer_step(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result + 10)

    @step(name="nested-outer-handler")
    async def nested_outer_handler(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=0)

    # Inner try/catch
    inner_try = workflow("inner-try") >> nested_inner_step
    inner_except = workflow("inner-except") >> nested_inner_handler
    inner_tc = try_catch("inner-tc").try_block(inner_try).except_block(inner_except).build()

    # Outer try/catch
    outer_try = workflow("outer-try") >> inner_tc >> nested_outer_step
    outer_except = workflow("outer-except") >> nested_outer_handler
    outer_tc = try_catch("outer-tc").try_block(outer_try).except_block(outer_except).build()

    wf = (workflow("nested-tc-flow") >> outer_tc).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]

    # Find outer try/catch
    outer_yaml = next((s for s in steps if "try_catch_outer-tc" in s), None)
    assert outer_yaml is not None
    outer_def = outer_yaml["try_catch_outer-tc"]

    # Check that inner try/catch is within outer try block
    outer_try_steps = outer_def["try"]["steps"]
    inner_tc_step = next((s for s in outer_try_steps if "try_catch_inner-tc" in s), None)
    assert inner_tc_step is not None

    # Verify inner try/catch structure
    inner_def = inner_tc_step["try_catch_inner-tc"]
    assert "try" in inner_def
    assert "except" in inner_def


def test_try_catch_without_except():
    """Test try/catch without except block (ignore errors)."""

    @step(name="optional")
    async def optional(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    try_block = workflow("try") >> optional
    tc_step = try_catch("ignore-errors").try_block(try_block).build()

    wf = (workflow("ignore-errors-flow") >> tc_step).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]
    tc_yaml = next((s for s in steps if "try_catch_ignore-errors" in s), None)
    assert tc_yaml is not None
    tc_def = tc_yaml["try_catch_ignore-errors"]

    # Should have empty except block
    assert "except" in tc_def
    assert tc_def["except"]["as"] == "e"
    assert tc_def["except"]["steps"] == []


def test_emit_workflow_yaml_with_try_catch():
    """Test that emit_workflow_yaml produces valid YAML with try/catch."""

    @step(name="yaml-main")
    async def yaml_main(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 3)

    @step(name="yaml-fallback")
    async def yaml_fallback(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=10)

    try_block = workflow("try") >> yaml_main
    except_block = workflow("except") >> yaml_fallback

    tc_step = try_catch("safe-main").try_block(try_block).except_block(except_block).build()

    wf = (workflow("yaml-tc-flow") >> tc_step).build()

    with TemporaryDirectory() as tmpdir:
        path = emit_workflow_yaml(wf, Path(tmpdir))
        assert path.exists()

        # Load and verify YAML
        with open(path) as f:
            yaml_content = yaml.safe_load(f)

        assert yaml_content is not None
        steps = yaml_content["main"]["steps"]

        # Find try/catch step
        tc_step = next((s for s in steps if any("try_catch_safe-main" in k for k in s)), None)
        assert tc_step is not None

        tc_config = tc_step["try_catch_safe-main"]
        assert "try" in tc_config
        assert "except" in tc_config
        assert "steps" in tc_config["try"]
        assert "steps" in tc_config["except"]
        assert tc_config["except"]["as"] == "e"
