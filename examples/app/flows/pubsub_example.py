"""Example workflow demonstrating Pub/Sub connector support."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, step, workflow
from fastapi_cloudflow.core.connectors import pubsub_publish_step


class PublishRequest(BaseModel):
    topic: str
    payload: str


class PublishResult(BaseModel):
    message_ids: list[str]


@step(name="prepare-message")
async def prepare_message(ctx: Context, data: PublishRequest) -> PublishRequest:
    return data


publish_step = pubsub_publish_step(
    name="publish-topic",
    topic="projects/demo/topics/example",
    input_model=PublishRequest,
    data_field="payload",
)


PUBSUB_EXAMPLE_FLOW = (workflow("pubsub-example-flow") >> prepare_message >> publish_step).build()
