from pydantic import BaseModel

from fastapi_cloudflow.codegen.workflows import workflow_to_yaml_dict
from fastapi_cloudflow.core import AssignStep, HttpStep, workflow


class A(BaseModel):
    x: int


class B(BaseModel):
    y: int


def test_codegen_mixed_steps_and_headers():
    # Fake steps: an Assign, a Python step (implicit), and an HttpStep
    assign = AssignStep("adapt", A, B, expr={"y": "${payload.x}"})
    py_step = AssignStep("py-pass", B, B, expr={"y": "${payload.y}"})
    http = HttpStep("remote", B, B, method="POST", url='${sys.get_env("URL")}', headers={"X-Trace": "trace"})

    wf = workflow("mix").__rshift__(assign).__rshift__(py_step).__rshift__(http).build()
    data = workflow_to_yaml_dict(wf)
    steps = data["main"]["steps"]
    # Verify first call step has X-Workflow-Name header
    first_call = next(s for s in steps if list(s.keys())[0].startswith("call_"))
    args = list(first_call.values())[0]["args"]
    headers = args["headers"]
    assert "X-Workflow-Name" in headers
    # Ensure capture_run_id exists
    assert any("capture_run_id_" in list(s.keys())[0] for s in steps)
