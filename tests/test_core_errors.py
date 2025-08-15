import asyncio

import pytest
from pydantic import BaseModel

from fastapi_cloudflow.core import AssignStep, Context, WorkflowMeta, step


class A(BaseModel):
    x: int


class B(BaseModel):
    y: int


def test_step_calling_infra_native_raises():
    s = AssignStep("assign", A, B, expr={"y": "${payload.x}"})
    with pytest.raises(RuntimeError):
        asyncio.get_event_loop().run_until_complete(s(Context(request=None, workflow=WorkflowMeta()), A(x=1)))


def test_step_decorator_wrong_param_count():
    with pytest.raises(TypeError):

        async def bad(a: Context, b: A, c: A) -> B:  # type: ignore[no-redef]
            return B(y=1)

        step()(bad)


def test_step_decorator_wrong_input_type():
    with pytest.raises(TypeError):

        async def bad2(a: Context, b: int) -> B:  # type: ignore[no-redef]
            return B(y=1)

        step()(bad2)


def test_step_decorator_wrong_return_type():
    with pytest.raises(TypeError):

        async def bad3(a: Context, b: A) -> int:  # type: ignore[no-redef]
            return 1

        step()(bad3)
