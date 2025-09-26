"""Tests for retry policy YAML code generation."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from pydantic import BaseModel

from fastapi_cloudflow import Context, HttpStep, RetryPolicy, step, workflow
from fastapi_cloudflow.codegen.workflows import emit_workflow_yaml, workflow_to_yaml_dict


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


def test_retry_policy_yaml_emission():
    """Test that retry policies are correctly emitted in YAML."""

    @step(
        name="retry-step",
        retry=RetryPolicy(
            max_retries=3,
            initial_delay_s=2.0,
            max_delay_s=10.0,
            multiplier=2.0,
            predicate="http.default_retry_predicate",
        ),
        timeout=timedelta(seconds=30),
    )
    async def retry_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    wf = (workflow("retry-test-flow") >> retry_step).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    # Check main structure
    assert "main" in yaml_dict
    assert "steps" in yaml_dict["main"]

    # Find the step with retry
    steps = yaml_dict["main"]["steps"]
    call_step = next((s for s in steps if "call_retry-step" in s), None)
    assert call_step is not None

    step_def = call_step["call_retry-step"]
    assert "retry" in step_def

    retry_config = step_def["retry"]
    assert retry_config["predicate"] == "${http.default_retry_predicate}"
    assert retry_config["max_retries"] == 3
    assert "backoff" in retry_config
    assert retry_config["backoff"]["initial_delay"] == 2.0
    assert retry_config["backoff"]["max_delay"] == 10.0
    assert retry_config["backoff"]["multiplier"] == 2.0

    # Check timeout
    assert step_def["args"]["timeout"] == 30


def test_http_step_retry_yaml():
    """Test that HTTP steps with retry are correctly generated."""

    http_step = HttpStep(
        name="http-retry",
        input_model=InputModel,
        output_model=OutputModel,
        method="POST",
        url="https://api.example.com/test",
        retry=RetryPolicy.idempotent_http(),
        timeout=timedelta(seconds=60),
    )

    wf = (workflow("http-retry-flow") >> http_step).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]
    call_step = next((s for s in steps if "call_http-retry" in s), None)
    assert call_step is not None

    step_def = call_step["call_http-retry"]
    assert "retry" in step_def
    assert step_def["retry"]["max_retries"] == 5
    assert step_def["args"]["timeout"] == 60


def test_no_retry_policy():
    """Test that steps without retry policy don't emit retry config."""

    @step(name="no-retry")
    async def no_retry(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    wf = (workflow("no-retry-flow") >> no_retry).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]
    call_step = next((s for s in steps if "call_no-retry" in s), None)
    assert call_step is not None

    step_def = call_step["call_no-retry"]
    assert "retry" not in step_def


def test_multiple_steps_with_different_retry_policies():
    """Test workflow with multiple steps having different retry policies."""

    @step(name="multi-step1", retry=RetryPolicy(max_retries=2))
    async def multi_step1(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value + 1)

    @step(name="multi-step2", retry=RetryPolicy(max_retries=5, initial_delay_s=3.0))
    async def multi_step2(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result * 2)

    @step(name="multi-step3")
    async def multi_step3(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result + 10)

    wf = (workflow("multi-retry-flow") >> multi_step1 >> multi_step2 >> multi_step3).build()
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]

    # Check step1
    step1_call = next((s for s in steps if "call_multi-step1" in s), None)
    assert step1_call is not None
    assert step1_call["call_multi-step1"]["retry"]["max_retries"] == 2

    # Check step2
    step2_call = next((s for s in steps if "call_multi-step2" in s), None)
    assert step2_call is not None
    assert step2_call["call_multi-step2"]["retry"]["max_retries"] == 5
    assert step2_call["call_multi-step2"]["retry"]["backoff"]["initial_delay"] == 3.0

    # Check step3 (no retry)
    step3_call = next((s for s in steps if "call_multi-step3" in s), None)
    assert step3_call is not None
    assert "retry" not in step3_call["call_multi-step3"]


def test_emit_workflow_yaml_with_retry():
    """Test that emit_workflow_yaml produces valid YAML with retry config."""

    @step(name="yaml-retry-step", retry=RetryPolicy(max_retries=3), timeout=timedelta(seconds=45))
    async def yaml_retry_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    wf = (workflow("yaml-retry-flow") >> yaml_retry_step).build()

    with TemporaryDirectory() as tmpdir:
        path = emit_workflow_yaml(wf, Path(tmpdir))
        assert path.exists()

        # Load and verify YAML
        with open(path) as f:
            yaml_content = yaml.safe_load(f)

        assert yaml_content is not None
        steps = yaml_content["main"]["steps"]

        # Find retry step
        retry_step = next((s for s in steps if any("call_yaml-retry-step" in k for k in s)), None)
        assert retry_step is not None

        step_config = retry_step["call_yaml-retry-step"]
        assert "retry" in step_config
        assert step_config["retry"]["max_retries"] == 3
        assert step_config["args"]["timeout"] == 45
