"""Comprehensive tests for workflow.py core module to improve coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from fastapi_cloudflow import Context, Step, Workflow, get_registry, get_workflows, step, workflow
from fastapi_cloudflow.core.workflow import Registry, WorkflowBuilder


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


class DifferentModel(BaseModel):
    data: str


def test_step_reregistration_identical_definition_is_ignored():
    """Registering the same step definition twice should succeed."""
    registry = Registry()

    async def callable(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    step1 = Step("duplicate-name", InputModel, OutputModel, fn=callable)
    registry.register_step(step1)

    # Should be a no-op when the equivalent definition is registered
    step_clone = Step("duplicate-name", InputModel, OutputModel, fn=callable)
    registry.register_step(step_clone)

    assert registry.steps["duplicate-name"] is step1


def test_step_name_collision_still_raises_for_different_defs():
    """Registering steps with same name but different definitions should raise."""
    registry = Registry()

    async def callable(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    first = Step("callable-step", InputModel, OutputModel, fn=callable)
    registry.register_step(first)

    # Different definition (different function body)
    async def another_callable(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value + 1)

    different = Step("callable-step", InputModel, OutputModel, fn=another_callable)

    with pytest.raises(ValueError, match="Step name collision: callable-step"):
        registry.register_step(different)


def test_workflow_name_collision_different_steps():
    """Test that registering workflows with same name but different steps raises ValueError."""
    registry = Registry()

    step1 = Step("step1", InputModel, OutputModel)
    step2 = Step("step2", InputModel, OutputModel)
    step3 = Step("step3", InputModel, OutputModel)

    wf1 = Workflow("duplicate-workflow", [step1, step2])
    wf2 = Workflow("duplicate-workflow", [step1, step3])  # Different second step

    registry.register_workflow(wf1)

    with pytest.raises(ValueError, match="Workflow name collision: duplicate-workflow"):
        registry.register_workflow(wf2)


def test_workflow_name_collision_identical_steps():
    """Test that registering identical workflows (same name and steps) is allowed."""
    registry = Registry()

    step1 = Step("step1", InputModel, OutputModel)
    step2 = Step("step2", OutputModel, OutputModel)

    wf1 = Workflow("duplicate-workflow", [step1, step2])
    wf2 = Workflow("duplicate-workflow", [step1, step2])  # Identical steps

    registry.register_workflow(wf1)
    registry.register_workflow(wf2)  # Should not raise

    # Should only have one workflow registered
    assert len(registry.workflows) == 1


def test_registry_get_workflows():
    """Test Registry.get_workflows() method."""
    registry = Registry()

    step1 = Step("step1", InputModel, OutputModel)
    step2 = Step("step2", OutputModel, OutputModel)

    wf1 = Workflow("workflow1", [step1])
    wf2 = Workflow("workflow2", [step2])

    registry.register_workflow(wf1)
    registry.register_workflow(wf2)

    workflows = registry.get_workflows()
    assert len(workflows) == 2
    assert wf1 in workflows
    assert wf2 in workflows


def test_workflow_builder_type_mismatch():
    """Test that WorkflowBuilder raises TypeError on type mismatch."""

    @step(name="outputs-int")
    async def step1(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    @step(name="expects-string")
    async def step2(ctx: Context, data: DifferentModel) -> OutputModel:
        return OutputModel(result=len(data.data))

    builder = workflow("mismatched-types") >> step1

    with pytest.raises(
        TypeError, match="Type mismatch: outputs-int outputs OutputModel but expects-string expects DifferentModel"
    ):
        builder >> step2


def test_workflow_builder_no_steps():
    """Test that building a workflow with no steps raises ValueError."""
    builder = workflow("empty-workflow")

    with pytest.raises(ValueError, match="Workflow has no steps"):
        builder.build()


def test_step_decorator_wrong_parameter_count():
    """Test that @step decorator validates function has exactly 2 parameters."""

    with pytest.raises(TypeError, match="@step function must accept exactly two positional parameters"):

        @step(name="wrong-params")
        async def wrong_params_step(ctx: Context) -> OutputModel:  # Missing data parameter
            return OutputModel(result=1)


def test_step_decorator_wrong_input_type():
    """Test that @step decorator validates input parameter is BaseModel."""

    with pytest.raises(
        TypeError, match="@step function must type its second parameter as a Pydantic BaseModel subclass"
    ):

        @step(name="wrong-input-type")
        async def wrong_input_step(ctx: Context, data: str) -> OutputModel:  # str instead of BaseModel
            return OutputModel(result=1)


def test_step_decorator_wrong_output_type():
    """Test that @step decorator validates return type is BaseModel."""

    with pytest.raises(TypeError, match="@step function must return a Pydantic BaseModel subclass"):

        @step(name="wrong-output-type")
        async def wrong_output_step(ctx: Context, data: InputModel) -> str:  # str instead of BaseModel
            return "result"


def test_step_decorator_no_type_hints():
    """Test that @step decorator fails when type hints are missing."""

    # Test missing input type hint
    def no_input_hint(ctx, data) -> OutputModel:
        return OutputModel(result=1)

    # Manually make it async to avoid syntax issues
    async_no_input = AsyncMock(side_effect=no_input_hint)
    async_no_input.__name__ = "no_input_hint"

    with pytest.raises(TypeError):
        step(name="no-input-hint")(async_no_input)

    # Test missing output type hint
    def no_output_hint(ctx: Context, data: InputModel):
        return OutputModel(result=1)

    async_no_output = AsyncMock(side_effect=no_output_hint)
    async_no_output.__name__ = "no_output_hint"

    with pytest.raises(TypeError):
        step(name="no-output-hint")(async_no_output)


def test_get_workflows_function():
    """Test the module-level get_workflows() function."""
    # Clear registry first
    registry = get_registry()
    registry.workflows.clear()

    @step(name="test-step")
    async def test_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    wf1 = (workflow("test-workflow-1") >> test_step).build()
    wf2 = (workflow("test-workflow-2") >> test_step).build()

    workflows = get_workflows()
    assert len(workflows) >= 2  # May have workflows from other tests
    assert wf1 in workflows
    assert wf2 in workflows


def test_workflow_builder_with_initial_nodes():
    """Test WorkflowBuilder can be initialized with existing nodes."""
    step1 = Step("step1", InputModel, OutputModel)
    step2 = Step("step2", OutputModel, OutputModel)

    builder = WorkflowBuilder("test-workflow", [step1])
    builder = builder >> step2

    wf = builder.build()
    assert len(wf.nodes) == 2
    assert wf.nodes[0] == step1
    assert wf.nodes[1] == step2


def test_step_decorator_with_all_options():
    """Test @step decorator with all optional parameters."""
    from datetime import timedelta

    from fastapi_cloudflow import RetryPolicy

    @step(
        name="full-featured-step",
        retry=RetryPolicy(max_retries=3),
        timeout=timedelta(seconds=30),
        tags=["test", "example"],
    )
    async def full_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    assert full_step.name == "full-featured-step"
    assert full_step.retry is not None
    assert full_step.retry.max_retries == 3
    assert full_step.timeout == timedelta(seconds=30)
    assert "test" in full_step.tags
    assert "example" in full_step.tags


def test_step_decorator_auto_naming():
    """Test that @step decorator generates names from function name."""

    @step()  # No explicit name
    async def my_awesome_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    assert my_awesome_step.name == "my-awesome-step"  # Underscores replaced with hyphens
