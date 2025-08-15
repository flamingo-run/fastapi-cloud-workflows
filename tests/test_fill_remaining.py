from pydantic import BaseModel

from fastapi_cloudflow.core import Arg, Registry, Step, Workflow


def test_arg_str_and_paths_cover():
    s = str(Arg.env("X") / "v")
    assert s.startswith("${")
    t = str(Arg.env("X") + "v")
    assert t.startswith("${")


def test_registry_get_workflows_empty_and_add():
    r = Registry()
    assert r.get_workflows() == []

    class A(BaseModel):
        x: int

    w = Workflow("n", [Step("s", A, A, fn=None)])
    r.register_workflow(w)
    assert r.get_workflows()[0].name == "n"
