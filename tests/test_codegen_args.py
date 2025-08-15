from pydantic import BaseModel

from fastapi_cloudflow.codegen.workflows import workflow_to_yaml_dict
from fastapi_cloudflow.core import Arg, HttpStep, workflow


class In(BaseModel):
    a: int


class Out(BaseModel):
    b: int


def test_httpstep_headers_timeout_auth_merge():
    http = HttpStep(
        name="h",
        input_model=In,
        output_model=Out,
        method="GET",
        url=Arg.env("BASE") / "path",
        headers={"X-Trace": Arg.env("TRACE")},
        auth={"type": "OIDC", "audience": "aud"},
    )
    wf = (workflow("w") >> http).build()
    data = workflow_to_yaml_dict(wf)
    steps = data["main"]["steps"]
    args = list(next(s for s in steps if list(s.keys())[0].startswith("call_")).values())[0]["args"]
    assert args["headers"]["X-Workflow-Name"]
    assert args["headers"]["X-Trace"]
    assert args["auth"]["type"] == "OIDC"
