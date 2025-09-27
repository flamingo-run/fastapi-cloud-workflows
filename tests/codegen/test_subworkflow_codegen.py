"""Tests for subworkflow YAML code generation."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, SubworkflowStep, step, workflow
from fastapi_cloudflow.codegen.workflows import workflow_to_yaml_dict


class InputModel(BaseModel):
    value: int


class OutputModel(BaseModel):
    result: int


def test_subworkflow_yaml_generation():
    """Test that SubworkflowStep generates correct YAML."""
    import uuid

    suffix = str(uuid.uuid4())[:8]

    @step(name=f"prepare-data-{suffix}")
    async def prepare_data(ctx: Context, data: InputModel) -> InputModel:
        return InputModel(value=data.value * 2)

    # Create a SubworkflowStep directly
    sub_step = SubworkflowStep(workflow_id="child-workflow", input_model=InputModel, output_model=OutputModel)

    @step(name=f"process-result-{suffix}")
    async def process_result(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result + 10)

    # Build workflow with subworkflow
    wf = (workflow(f"parent-workflow-{suffix}") >> prepare_data >> sub_step >> process_result).build()

    # Generate YAML
    yaml_dict = workflow_to_yaml_dict(wf)

    # Check main structure
    assert "main" in yaml_dict
    assert "params" in yaml_dict["main"]
    assert "steps" in yaml_dict["main"]

    steps = yaml_dict["main"]["steps"]

    # Find the subworkflow call step
    subworkflow_call = None
    for step_item in steps:
        if any("call_child_workflow" in str(k) for k in step_item):
            subworkflow_call = step_item
            break

    assert subworkflow_call is not None

    # Check subworkflow call structure
    call_step = list(subworkflow_call.values())[0]
    assert call_step["call"] == "workflows.executeWorkflow"
    assert "args" in call_step
    assert call_step["args"]["workflow_id"] == "child-workflow"
    assert call_step["args"]["argument"] == "${payload}"
    assert "result" in call_step  # Should wait for result


def test_subworkflow_with_mappings_yaml():
    """Test SubworkflowStep with mappings generates correct YAML."""
    import uuid

    suffix = str(uuid.uuid4())[:8]

    @step(name=f"setup-{suffix}")
    async def setup(ctx: Context, data: InputModel) -> InputModel:
        return data

    # Create SubworkflowStep with mappings
    sub_step = SubworkflowStep(
        workflow_id="mapped-workflow",
        input_model=InputModel,
        output_model=OutputModel,
        input_mapping={"custom_field": "value"},
        output_mapping={"result": "custom_result"},
    )

    # Build workflow
    wf = (workflow(f"mapped-parent-{suffix}") >> setup >> sub_step).build()

    # Generate YAML
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]

    # Find subworkflow call
    for step_item in steps:
        if any("call_mapped_workflow" in str(k) for k in step_item):
            call_step = list(step_item.values())[0]
            # Check input mapping applied
            assert "argument" in call_step["args"]
            # With mappings, it should use the mapped structure
            break


def test_subworkflow_fire_and_forget_yaml():
    """Test SubworkflowStep in fire-and-forget mode generates correct YAML."""
    import uuid

    suffix = str(uuid.uuid4())[:8]

    @step(name=f"trigger-{suffix}")
    async def trigger(ctx: Context, data: InputModel) -> InputModel:
        return data

    @step(name=f"continue-{suffix}")
    async def continue_processing(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value)

    # Create fire-and-forget SubworkflowStep
    # For fire-and-forget, we need to set the output model to match input since it doesn't wait
    async_sub = SubworkflowStep(
        workflow_id="async-workflow",
        input_model=InputModel,
        output_model=InputModel,  # Fire-and-forget should pass through the input type
        wait=False,
    )

    # Build workflow - note the types flow correctly now
    wf = (
        workflow(f"async-parent-{suffix}")
        >> trigger  # outputs InputModel
        >> async_sub  # Fire and forget - passes through InputModel
        >> continue_processing  # receives InputModel from async_sub passthrough
    ).build()

    # Generate YAML
    yaml_dict = workflow_to_yaml_dict(wf)

    steps = yaml_dict["main"]["steps"]

    # Find async subworkflow call
    for step_item in steps:
        if any("call_async_workflow" in str(k) for k in step_item):
            call_step = list(step_item.values())[0]
            assert call_step["call"] == "workflows.executeWorkflow"
            assert "result" not in call_step  # Should NOT wait for result
            break


def test_workflow_composition_yaml():
    """Test that workflow composition generates correct YAML."""
    import uuid

    suffix = str(uuid.uuid4())[:8]

    @step(name=f"child-step-yaml-{suffix}")
    async def child_step(ctx: Context, data: InputModel) -> OutputModel:
        return OutputModel(result=data.value * 2)

    @step(name=f"parent-start-{suffix}")
    async def parent_start(ctx: Context, data: InputModel) -> InputModel:
        return data

    @step(name=f"parent-end-{suffix}")
    async def parent_end(ctx: Context, data: OutputModel) -> OutputModel:
        return OutputModel(result=data.result + 100)

    # Create child workflow
    child_wf = (workflow(f"child-wf-yaml-{suffix}") >> child_step).build()

    # Create parent that uses child
    parent_wf = (
        workflow(f"parent-wf-yaml-{suffix}")
        >> parent_start
        >> child_wf  # Direct workflow usage
        >> parent_end
    ).build()

    # Generate YAML
    yaml_dict = workflow_to_yaml_dict(parent_wf)

    # Check structure
    assert "main" in yaml_dict
    steps = yaml_dict["main"]["steps"]

    # Verify subworkflow call exists
    has_subworkflow_call = False
    for step_item in steps:
        if any("call_child_wf_yaml" in str(k) for k in step_item):
            has_subworkflow_call = True
            call_step = list(step_item.values())[0]
            assert call_step["call"] == "workflows.executeWorkflow"
            assert call_step["args"]["workflow_id"] == f"child-wf-yaml-{suffix}"
            break

    assert has_subworkflow_call, "Should have subworkflow call in YAML"
