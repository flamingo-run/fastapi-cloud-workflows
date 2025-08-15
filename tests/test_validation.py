import pytest
from pydantic import BaseModel

from fastapi_cloudflow.core import Context, step, workflow


class A(BaseModel):
    x: int


class B(BaseModel):
    y: int


class C(BaseModel):
    z: int


@step(name="to-b")
async def to_b(ctx: Context, data: A) -> B:
    return B(y=data.x)


@step(name="needs-c")
async def needs_c(ctx: Context, data: C) -> C:
    return data


def test_type_mismatch_raises():
    with pytest.raises(TypeError):
        _ = (workflow("mismatch-flow") >> to_b >> needs_c).build()
