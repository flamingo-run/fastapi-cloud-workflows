from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, TypeVar, get_type_hints

from pydantic import BaseModel

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


@dataclass
class WorkflowMeta:
    name: str | None = None
    step: str | None = None
    run_id: str | None = None


@dataclass
class Context:
    request: Any
    workflow: WorkflowMeta


@dataclass
class RetryPolicy:
    max_retries: int = 5
    initial_delay_s: float = 1.0
    max_delay_s: float = 30.0
    multiplier: float = 2.0
    predicate: str = "http.default_retry_predicate"

    @staticmethod
    def idempotent_http() -> RetryPolicy:
        return RetryPolicy(
            max_retries=5,
            initial_delay_s=1.0,
            max_delay_s=30.0,
            multiplier=2.0,
            predicate="http.default_retry_predicate",
        )


class ArgExpr:
    def __init__(self, expr: str) -> None:
        self.expr = expr

    @staticmethod
    def _coerce_expr(value: str | ArgExpr) -> str:
        if isinstance(value, ArgExpr):
            return value.expr
        return f'"{value}"'

    def __truediv__(self, other: str | ArgExpr) -> ArgExpr:
        # Coalesce when joining with a plain literal
        if isinstance(other, ArgExpr):
            right = other.expr
            return ArgExpr(f'{self.expr} + "/" + {right}')
        else:
            return ArgExpr(f'{self.expr} + "/{other}"')

    def __add__(self, other: str | ArgExpr) -> ArgExpr:
        right = self._coerce_expr(other)
        return ArgExpr(f"{self.expr} + {right}")

    def __str__(self) -> str:
        return f"${{{self.expr}}}"


class Arg:
    @staticmethod
    def env(name: str) -> ArgExpr:
        return ArgExpr(f'sys.get_env("{name}")')

    @staticmethod
    def param(path: str) -> ArgExpr:
        return ArgExpr(f"params.{path}")

    @staticmethod
    def ctx(key: str) -> ArgExpr:
        # runtime-only; to be explicitly mapped when compiling
        return ArgExpr(f"ctx.{key}")


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
        fn: Callable[[Context, InT], Awaitable[OutT]] | None,
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

    async def __call__(self, ctx: Context, data: InT) -> OutT:  # type: ignore[override]
        if self.fn is None:
            raise RuntimeError("Step is not callable (infra-native or missing fn)")
        return await self.fn(ctx, data)


class AssignStep(Step[InT, OutT]):
    def __init__(self, name: str, input_model: type[InT], output_model: type[OutT], expr: dict[str, Any]) -> None:
        super().__init__(name, input_model, output_model, fn=None)
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
        super().__init__(name, input_model, output_model, fn=None, retry=retry, timeout=timeout)
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.auth = auth


class ModelAdapter(Step[InT, OutT]):
    def __init__(self, name: str, input_model: type[InT], output_model: type[OutT], mapping: dict[str, Any]) -> None:
        super().__init__(name, input_model, output_model, fn=None)
        self.mapping = mapping


class Workflow:
    def __init__(self, name: str, nodes: list[Step[Any, Any]]) -> None:
        self.name = name
        self.nodes = nodes


class Registry:
    def __init__(self) -> None:
        self.steps: dict[str, Step[Any, Any]] = {}
        self.workflows: dict[str, Workflow] = {}

    # Steps
    def register_step(self, step: Step[Any, Any]) -> None:
        if step.name in self.steps:
            raise ValueError(f"Step name collision: {step.name}")
        self.steps[step.name] = step

    # Workflows
    def register_workflow(self, workflow: Workflow) -> None:
        existing = self.workflows.get(workflow.name)
        if existing is not None:
            # Idempotent if identical sequence of step names
            existing_names = [s.name for s in existing.nodes]
            new_names = [s.name for s in workflow.nodes]
            if existing_names == new_names:
                return
            raise ValueError(f"Workflow name collision: {workflow.name}")
        self.workflows[workflow.name] = workflow

    def get_workflows(self) -> list[Workflow]:
        return list(self.workflows.values())


class WorkflowBuilder:
    def __init__(self, name: str, nodes: list[Step[Any, Any]] | None = None) -> None:
        self.name = name
        self.nodes = nodes or []

    def __rshift__(self, other: Step[Any, Any]) -> WorkflowBuilder:
        # Minimal continuity check: exact model type match
        if self.nodes:
            prev = self.nodes[-1]
            if prev.output_model is not other.input_model:
                raise TypeError(
                    f"Type mismatch: {prev.name} outputs {prev.output_model.__name__} "
                    f"but {other.name} expects {other.input_model.__name__}"
                )
        return WorkflowBuilder(self.name, self.nodes + [other])

    def build(self) -> Workflow:
        if not self.nodes:
            raise ValueError("Workflow has no steps")
        wf = Workflow(self.name, self.nodes)
        _REGISTRY.register_workflow(wf)
        return wf


_REGISTRY = Registry()


def workflow(name: str) -> WorkflowBuilder:
    return WorkflowBuilder(name)


def step(
    *,
    name: str | None = None,
    retry: RetryPolicy | None = None,
    timeout: timedelta | None = None,
    tags: Iterable[str] = (),
):
    def decorator(fn: Callable[[Context, InT], Awaitable[OutT]]) -> Step[InT, OutT]:
        # Resolve annotations robustly (handles postponed annotations)
        hints = get_type_hints(fn)
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        if len(params) != 2:
            raise TypeError("@step function must accept exactly two positional parameters: (Context, InModel)")
        in_param = params[1].name
        in_model = hints.get(in_param)
        out_model = hints.get("return")
        if not (isinstance(in_model, type) and issubclass(in_model, BaseModel)):
            raise TypeError("@step function must type its second parameter as a Pydantic BaseModel subclass")
        if not (isinstance(out_model, type) and issubclass(out_model, BaseModel)):
            raise TypeError("@step function must return a Pydantic BaseModel subclass")
        base_name = getattr(fn, "__name__", "step")
        nm = name or base_name.replace("_", "-")
        s: Step[Any, Any] = Step(nm, in_model, out_model, fn=fn, retry=retry, timeout=timeout, tags=tags)
        _REGISTRY.register_step(s)
        return s

    return decorator


def get_registry() -> Registry:
    return _REGISTRY


def get_workflows() -> list[Workflow]:
    return _REGISTRY.get_workflows()
