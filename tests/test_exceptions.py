import pytest
from pydantic import BaseModel

from fastapi_cloudflow.core import Context, WorkflowMeta, step, workflow


class A(BaseModel):
    x: int


class B(BaseModel):
    y: int


@step(name="boom")
async def boom(ctx: Context, data: A) -> B:
    raise RuntimeError("explode")


def test_runtime_exception_propagates():
    (workflow("boom-flow") >> boom).build()
    # We only test that build passes; runtime exceptions are raised when calling fn
    with pytest.raises(RuntimeError):
        import asyncio

        asyncio.get_event_loop().run_until_complete(boom(Context(request=None, workflow=WorkflowMeta()), A(x=1)))
