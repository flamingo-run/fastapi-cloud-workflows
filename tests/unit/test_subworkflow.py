"""Tests for subworkflow functionality."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, SubworkflowStep, get_workflow_dependencies, step, workflow


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


def test_subworkflow_step_creation():
    """Test creating a SubworkflowStep."""
    sub_step = SubworkflowStep(
        workflow_id="child-workflow",
        input_model=InputModel,
        output_model=OutputModel,
    )

    assert sub_step.workflow_id == "child-workflow"
    assert sub_step.name == "call_child_workflow"
    assert sub_step.input_model == InputModel
    assert sub_step.output_model == OutputModel
    assert sub_step.wait is True
    assert sub_step.fn is None  # Subworkflows are not callable


def test_workflow_to_subworkflow_step():
    """Test converting a Workflow to a SubworkflowStep."""

    @step(name="step1")
    async def step1(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    @step(name="step2")
    async def step2(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result + 10)

    child_wf = (workflow("child-workflow") >> step1 >> step2).build()

    # Convert to subworkflow step
    sub_step = child_wf.to_subworkflow_step()

    assert isinstance(sub_step, SubworkflowStep)
    assert sub_step.workflow_id == "child-workflow"
    assert sub_step.input_model == InputModel
    assert sub_step.output_model == OutputModel


def test_workflow_composition_with_subworkflow():
    """Test composing workflows using subworkflows."""
    import uuid

    # Use unique names to avoid collisions on retries
    suffix = str(uuid.uuid4())[:8]

    @step(name=f"comp-child-step-{suffix}")
    async def child_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    @step(name=f"comp-parent-step1-{suffix}")
    async def parent_step1(ctx: Context, data: InputModel) -> InputModel:
        return InputModel(value=data.value + 5)

    @step(name=f"comp-parent-step2-{suffix}")
    async def parent_step2(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result * 3)

    # Create child workflow
    child_wf = (workflow(f"child-workflow-{suffix}") >> child_step).build()

    # Create parent workflow that uses child
    parent_wf = (
        workflow(f"parent-workflow-{suffix}")
        >> parent_step1
        >> child_wf  # Use child workflow directly
        >> parent_step2
    ).build()

    # Check that parent has 3 steps (parent_step1, subworkflow call, parent_step2)
    assert len(parent_wf.nodes) == 3
    assert parent_wf.nodes[0].name == f"comp-parent-step1-{suffix}"
    assert isinstance(parent_wf.nodes[1], SubworkflowStep)
    assert parent_wf.nodes[1].workflow_id == f"child-workflow-{suffix}"
    assert parent_wf.nodes[2].name == f"comp-parent-step2-{suffix}"

    # Check dependency tracking
    assert f"child-workflow-{suffix}" in parent_wf.dependencies


def test_workflow_dependencies_tracking():
    """Test that workflow dependencies are tracked correctly."""
    import uuid

    from fastapi_cloudflow import get_registry

    # Clear registry
    registry = get_registry()
    registry.workflows.clear()

    # Use unique names to avoid collisions on retries
    suffix = str(uuid.uuid4())[:8]

    @step(name=f"dep-s1-{suffix}")
    async def s1(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    @step(name=f"dep-s2-{suffix}")
    async def s2(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result)

    @step(name=f"s3-{suffix}")
    async def s3(ctx: Context, data: OutputModel) -> InputModel:
        return InputModel(value=data.result)

    # Create multiple workflows
    wf1 = (workflow("wf1") >> s1).build()
    wf2 = (workflow("wf2") >> s1).build()
    (workflow("wf3") >> s1 >> s3 >> wf1 >> s2).build()  # wf3 depends on wf1
    (workflow("wf4") >> s1 >> s3 >> wf2 >> s3 >> wf1 >> s2).build()  # wf4 depends on wf1 and wf2

    # Get dependency graph
    deps = get_workflow_dependencies()

    assert "wf1" not in deps or len(deps.get("wf1", set())) == 0  # wf1 has no dependencies
    assert "wf2" not in deps or len(deps.get("wf2", set())) == 0  # wf2 has no dependencies
    assert deps["wf3"] == {"wf1"}
    assert deps["wf4"] == {"wf1", "wf2"}


def test_subworkflow_with_mappings():
    """Test SubworkflowStep with input and output mappings."""

    sub_step = SubworkflowStep(
        workflow_id="mapped-workflow",
        input_model=InputModel,
        output_model=OutputModel,
        input_mapping={"value": "${payload.custom_value}"},
        output_mapping={"custom_result": "result"},
    )

    assert sub_step.input_mapping == {"value": "${payload.custom_value}"}
    assert sub_step.output_mapping == {"custom_result": "result"}


def test_subworkflow_fire_and_forget():
    """Test SubworkflowStep in fire-and-forget mode."""

    sub_step = SubworkflowStep(
        workflow_id="async-workflow",
        input_model=InputModel,
        output_model=OutputModel,
        wait=False,  # Fire-and-forget mode
    )

    assert sub_step.wait is False
    assert sub_step.workflow_id == "async-workflow"
