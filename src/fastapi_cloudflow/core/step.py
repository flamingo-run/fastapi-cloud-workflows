import hashlib
import inspect
from collections.abc import Awaitable, Callable, Iterable
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel

from fastapi_cloudflow.core.arg import ArgExpr
from fastapi_cloudflow.core.types import ConnectorCall, Context, RetryPolicy

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
        self.fingerprint = self._compute_fingerprint()

    async def __call__(self, ctx: Context, data: InT) -> OutT:
        if self.fn is None:
            raise RuntimeError("Step is not callable. Is it a native step?")
        return await self.fn(ctx, data)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Step):
            return False
        return self.fingerprint == other.fingerprint

    def _compute_fingerprint(self) -> str:
        hasher = hashlib.sha256()
        hasher.update(self.name.encode("utf-8"))
        hasher.update(self._model_hash(self.input_model))
        hasher.update(self._model_hash(self.output_model))
        hasher.update(self._function_hash(self.fn))
        hasher.update(repr(sorted(self.tags)).encode("utf-8"))
        hasher.update(repr(self.timeout).encode("utf-8"))
        if self.retry is not None:
            retry_tuple = (
                self.retry.max_retries,
                self.retry.initial_delay_s,
                self.retry.max_delay_s,
                self.retry.multiplier,
                self.retry.predicate,
            )
            hasher.update(repr(retry_tuple).encode("utf-8"))
        return hasher.hexdigest()

    @staticmethod
    def _model_hash(model: type[BaseModel] | None) -> bytes:
        if model is None:
            return b"none"
        schema = model.model_json_schema()
        payload = (
            getattr(model, "__qualname__", getattr(model, "__name__", "")),
            schema,
        )
        return repr(payload).encode("utf-8")

    @staticmethod
    def _function_hash(fn: Callable[[Context, InT], Awaitable[OutT]] | None) -> bytes:
        if fn is None:
            return b"none"
        parts: list[str] = []
        parts.append(getattr(fn, "__qualname__", getattr(fn, "__name__", "")))
        try:
            source = inspect.getsource(fn)
        except (OSError, TypeError):
            source = None
        if source:
            parts.append(source.strip())
        code_obj = getattr(fn, "__code__", None)
        if code_obj is not None:
            parts.append(repr(code_obj.co_consts))
            parts.append(repr(code_obj.co_code))
        defaults = getattr(fn, "__defaults__", None)
        if defaults:
            parts.append(repr(defaults))
        kwdefaults = getattr(fn, "__kwdefaults__", None)
        if kwdefaults:
            parts.append(repr(sorted(kwdefaults.items())))
        return "|".join(parts).encode("utf-8")


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


class ConnectorStep(Step[InT, OutT]):
    def __init__(
        self,
        name: str,
        input_model: type[InT],
        output_model: type[OutT],
        call: ConnectorCall,
        retry: RetryPolicy | None = None,
        timeout: timedelta | None = None,
    ) -> None:
        super().__init__(
            name=name, input_model=input_model, output_model=output_model, fn=None, retry=retry, timeout=timeout
        )
        self.call = call


class ModelAdapter(Step[InT, OutT]):
    def __init__(self, name: str, input_model: type[InT], output_model: type[OutT], mapping: dict[str, Any]) -> None:
        super().__init__(name=name, input_model=input_model, output_model=output_model, fn=None)
        self.mapping = mapping
