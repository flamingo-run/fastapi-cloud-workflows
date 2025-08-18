from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi_cloudflow import Arg, Context, HttpStep, step, workflow


class EchoIn(BaseModel):
    name: str


class HttpbinRes(BaseModel):
    # Avoid shadowing BaseModel methods by using an alias
    model_config = {"populate_by_name": True}
    json_: dict = Field(alias="json")


class EchoOut(BaseModel):
    echoed_name: str


class NameShout(BaseModel):
    name_upper: str
    length: int


httpbin_echo = HttpStep(
    name="external-echo",
    input_model=EchoIn,
    output_model=HttpbinRes,
    method="POST",
    # Use a public echo endpoint (httpbin) via env, default set at deploy
    url=Arg.env("ECHO_URL"),
)


@step(name="extract-name")
async def adapt_echo(ctx: Context, data: HttpbinRes) -> EchoOut:
    # httpbin returns payload under the "json" key
    name = str(data.json_.get("name", ""))
    return EchoOut(echoed_name=name)


@step(name="name-shout")
async def name_shout(ctx: Context, data: EchoOut) -> NameShout:
    up = data.echoed_name.upper()
    return NameShout(name_upper=up, length=len(up))


ECHO_NAME_FLOW = (workflow("echo-name-flow") >> httpbin_echo >> adapt_echo >> name_shout).build()
