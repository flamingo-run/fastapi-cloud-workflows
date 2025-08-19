from collections.abc import Awaitable, Callable, Iterable
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel

from fastapi_cloudflow.core.arg import ArgExpr
from fastapi_cloudflow.core.types import Context, RetryPolicy

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


class Step[InT: BaseModel, OutT: BaseModel]:
    name: str
    input_model: type[InT]
    output_model: type[OutT]
    retry: RetryPolicy | None
    timeout: timedelta | None
    tags: set[str]

    def __init__(
        self,
        name: str,
        input_model: type[InT],
        output_model: type[OutT],
        fn: Callable[[Context, InT], Awaitable[OutT]] | None = None,
        retry: RetryPolicy | None = None,
        timeout: timedelta | None = None,
        tags: Iterable[str] = (),
    ) -> None:
        self.name = name
        self.input_model = input_model
        self.output_model = output_model
        self.fn = fn
        self.retry = retry
        self.timeout = timeout
        self.tags = set(tags)

    async def __call__(self, ctx: Context, data: InT) -> OutT:
        if self.fn is None:
            raise RuntimeError("Step is not callable. Is it a native step?")
        return await self.fn(ctx, data)


class AssignStep(Step[InT, OutT]):
    def __init__(self, name: str, input_model: type[InT], output_model: type[OutT], expr: dict[str, Any]) -> None:
        super().__init__(name=name, input_model=input_model, output_model=output_model, fn=None)
        self.expr = expr


class HttpStep(Step[InT, OutT]):
    def __init__(
        self,
        name: str,
        input_model: type[InT],
        output_model: type[OutT],
        method: str,
        url: str | ArgExpr,
        headers: dict[str, str | ArgExpr] | None = None,
        auth: dict[str, Any] | None = None,
        retry: RetryPolicy | None = None,
        timeout: timedelta | None = None,
    ) -> None:
        super().__init__(
            name=name,
            input_model=input_model,
            output_model=output_model,
            fn=None,
            retry=retry,
            timeout=timeout,
        )
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.auth = auth


class ModelAdapter(Step[InT, OutT]):
    def __init__(self, name: str, input_model: type[InT], output_model: type[OutT], mapping: dict[str, Any]) -> None:
        super().__init__(name=name, input_model=input_model, output_model=output_model, fn=None)
        self.mapping = mapping
