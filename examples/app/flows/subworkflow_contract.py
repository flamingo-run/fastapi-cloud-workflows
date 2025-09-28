from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, SubworkflowStep, step, workflow


class SubworkflowInput(BaseModel):
    value: int


class SubworkflowResult(BaseModel):
    result: int


@step(name="subwf-prepare")
async def subwf_prepare(ctx: Context, data: SubworkflowInput) -> SubworkflowInput:
    return SubworkflowInput(value=data.value + 2)


SUB_WORKFLOW = SubworkflowStep(
    workflow_id="subwf-child",
    input_model=SubworkflowInput,
    output_model=SubworkflowResult,
    input_mapping={"custom_field": "${payload.value}"},
    output_mapping={"result": "custom_result"},
)


@step(name="subwf-finalize")
async def subwf_finalize(ctx: Context, data: SubworkflowResult) -> SubworkflowResult:
    return SubworkflowResult(result=data.result + 5)


SUBWORKFLOW_DEMO = (workflow("subworkflow-demo") >> subwf_prepare >> SUB_WORKFLOW >> subwf_finalize).build()
