"""Helpers for Google Cloud connector steps."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel

from fastapi_cloudflow.core.arg import Arg, ArgExpr
from fastapi_cloudflow.core.step import ConnectorStep
from fastapi_cloudflow.core.types import ConnectorCall, RetryPolicy

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


_PUBSUB_TOPIC_PREFIX = "projects/"


def _validate_topic_path(topic: str) -> None:
    if not topic.startswith(_PUBSUB_TOPIC_PREFIX):
        raise ValueError("Pub/Sub topic must be fully qualified: 'projects/<project>/topics/<topic_id>'")
    parts = topic.split("/")
    if len(parts) != 4:
        raise ValueError("Pub/Sub topic must follow 'projects/<project>/topics/<topic_id>' format")
    _, project, resource, topic_id = parts
    if not project or resource != "topics" or not topic_id:
        raise ValueError("Pub/Sub topic must include non-empty project and topic id")


def pubsub_message(
    *,
    data: str | ArgExpr,
    attributes: Mapping[str, str | ArgExpr] | ArgExpr | None = None,
    ordering_key: str | ArgExpr | None = None,
) -> dict[str, Any]:
    """Build a Pub/Sub message payload for the publish API."""

    message: dict[str, Any] = {"data": Arg.base64(data)}

    if attributes is not None:
        if isinstance(attributes, ArgExpr):
            message["attributes"] = attributes
        else:
            message["attributes"] = attributes.copy()

    if ordering_key is not None:
        message["orderingKey"] = ordering_key

    return message


def pubsub_publish(
    *,
    topic: str | ArgExpr,
    data: str | ArgExpr | None = None,
    attributes: Mapping[str, str | ArgExpr] | ArgExpr | None = None,
    ordering_key: str | ArgExpr | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> ConnectorCall:
    """Create a ConnectorCall for the Pub/Sub publish API."""

    if isinstance(topic, str):
        _validate_topic_path(topic)

    if messages is None:
        if data is None:
            raise ValueError("Provide either `data` or `messages` when publishing to Pub/Sub")
        messages = [pubsub_message(data=data, attributes=attributes, ordering_key=ordering_key)]

    request: dict[str, Any] = {
        "topic": topic,
        "messages": messages,
    }

    args: dict[str, Any] = {
        "connector": "googleapis.pubsub.v1",
        "operation": "projects.topics.publish",
        "request": request,
    }

    return ConnectorCall(call="connectors.googleapis.pubsub.v1.projects.topics.publish", args=args)


class PubSubPublishResult(BaseModel):
    message_ids: list[str]


def pubsub_publish_step[InT: BaseModel, OutT: BaseModel](
    *,
    name: str,
    topic: str,
    input_model: type[InT],
    output_model: type[OutT] | None = None,
    data: str | ArgExpr | None = None,
    data_field: str | None = "payload",
    attributes: Mapping[str, str | ArgExpr] | ArgExpr | None = None,
    attributes_field: str | None = None,
    ordering_key: str | ArgExpr | None = None,
    ordering_key_field: str | None = None,
    retry: RetryPolicy | None = None,
    timeout: timedelta | None = None,
) -> ConnectorStep[InT, OutT]:
    """High-level helper that returns a ConnectorStep publishing to Pub/Sub."""

    if isinstance(topic, str):
        _validate_topic_path(topic)

    data_expr: str | ArgExpr | None = data
    if data_expr is None:
        if not data_field:
            raise ValueError("Provide either `data` or `data_field` for pubsub_publish_step")
        data_expr = Arg.param(data_field)

    attributes_expr = attributes
    if attributes_expr is None and attributes_field is not None:
        attributes_expr = Arg.param(attributes_field)

    ordering_expr = ordering_key
    if ordering_expr is None and ordering_key_field is not None:
        ordering_expr = Arg.param(ordering_key_field)

    call = pubsub_publish(
        topic=topic,
        data=data_expr,
        attributes=attributes_expr,
        ordering_key=ordering_expr,
    )

    result_model = output_model or PubSubPublishResult  # type: ignore[assignment]

    return ConnectorStep(
        name=name,
        input_model=input_model,
        output_model=result_model,
        call=call,
        retry=retry,
        timeout=timeout,
    )


__all__ = ["pubsub_publish", "pubsub_message", "pubsub_publish_step", "PubSubPublishResult"]
