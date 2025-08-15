from pydantic import BaseModel

from fastapi_cloudflow.core import Context, get_workflows, step, workflow


class I1(BaseModel):
    a: int


class O1(BaseModel):
    b: int


class O2(BaseModel):
    c: int


@step(name="s1")
async def s1(ctx: Context, data: I1) -> O1:
    return O1(b=data.a + 1)


@step(name="s2")
async def s2(ctx: Context, data: O1) -> O2:
    return O2(c=data.b + 1)


def test_multiple_workflows_register_independently():
    (workflow("wf-1") >> s1).build()
    (workflow("wf-2") >> s1 >> s2).build()
    names = {w.name for w in get_workflows()}
    assert {"wf-1", "wf-2"}.issubset(names)
