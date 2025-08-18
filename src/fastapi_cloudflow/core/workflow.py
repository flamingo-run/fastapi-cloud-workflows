from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, TypeVar, get_type_hints

from pydantic import BaseModel

from fastapi_cloudflow.core.step import Step
from fastapi_cloudflow.core.types import Context


class Workflow:
    def __init__(self, name: str, nodes: list[Step[Any, Any]]) -> None:
        self.name = name
        self.nodes = nodes


class Registry:
    def __init__(self) -> None:
        self.steps: dict[str, Step[Any, Any]] = {}
        self.workflows: dict[str, Workflow] = {}

    def register_step(self, step: Step[Any, Any]) -> None:
        if step.name in self.steps:
            raise ValueError(f"Step name collision: {step.name}")
        self.steps[step.name] = step

    def register_workflow(self, workflow: Workflow) -> None:
        existing = self.workflows.get(workflow.name)
        if existing is not None:
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


InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


def step(
    *,
    name: str | None = None,
    retry: Any | None = None,
    timeout: Any | None = None,
    tags: Iterable[str] = (),
):
    def decorator(fn: Callable[[Context, InT], Awaitable[OutT]]) -> Step[InT, OutT]:
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
