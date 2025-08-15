import pytest
from pydantic import BaseModel

from fastapi_cloudflow.core import Registry, Step, Workflow


class A(BaseModel):
    x: int


class B(BaseModel):
    y: int


def test_registry_collisions():
    reg = Registry()
    s1 = Step("dup", A, B, fn=None)
    reg.register_step(s1)
    with pytest.raises(ValueError):
        reg.register_step(s1)

    wf = Workflow("wf", [s1])
    reg.register_workflow(wf)
    # Idempotent re-registration of identical workflow is allowed
    reg.register_workflow(Workflow("wf", [s1]))

    # Collision when sequence differs
    s2 = Step("other", A, B, fn=None)
    with pytest.raises(ValueError):
        reg.register_workflow(Workflow("wf", [s2]))
