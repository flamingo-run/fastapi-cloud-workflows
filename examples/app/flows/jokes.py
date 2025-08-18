from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi_cloudflow import Context, HttpStep, step, workflow


class EmptyIn(BaseModel):
    pass


class JokeAPIRes(BaseModel):
    id: str
    joke: str
    status: int


class JokeBits(BaseModel):
    setup: str
    punch: str


joke_fetch = HttpStep(
    name="joke-fetch",
    input_model=EmptyIn,
    output_model=JokeAPIRes,
    method="GET",
    url="https://icanhazdadjoke.com/",
    headers={"Accept": "application/json"},
)


@step(name="joke-split")
async def joke_split(ctx: Context, data: JokeAPIRes) -> JokeBits:
    j = data.joke or ""
    mid = len(j) // 2
    return JokeBits(setup=j[:mid], punch=j[mid:])


class JokeRated(BaseModel):
    setup: str
    punch: str
    rating: int = Field(ge=0, le=10)


@step(name="joke-rate")
async def joke_rate(ctx: Context, data: JokeBits) -> JokeRated:
    rating = (len(data.setup) + len(data.punch)) % 11
    return JokeRated(setup=data.setup, punch=data.punch, rating=rating)


JOKE_FLOW = (workflow("joke-flow") >> joke_fetch >> joke_split >> joke_rate).build()
