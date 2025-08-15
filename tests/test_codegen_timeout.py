from datetime import timedelta

from pydantic import BaseModel

from fastapi_cloudflow.codegen.workflows import workflow_to_yaml_dict
from fastapi_cloudflow.core import Arg, HttpStep, workflow


class In(BaseModel):
    a: int


class Out(BaseModel):
    b: int


def test_httpstep_timeout_emitted():
    http = HttpStep("h", In, Out, method="GET", url=Arg.env("BASE"), timeout=timedelta(seconds=5))
    wf = (workflow("w2") >> http).build()
    data = workflow_to_yaml_dict(wf)
    call = next(s for s in data["main"]["steps"] if list(s.keys())[0].startswith("call_"))
    args = list(call.values())[0]["args"]
    assert args["timeout"] == 5
