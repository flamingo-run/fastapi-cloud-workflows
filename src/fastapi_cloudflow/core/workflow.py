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
        self.dependencies: set[str] = set()

    def to_subworkflow_step(self) -> Step[Any, Any]:
        """Convert this workflow to a SubworkflowStep for composition."""
        from fastapi_cloudflow.core.subworkflow import SubworkflowStep

        # Get input/output models from first and last steps
        if not self.nodes:
            raise ValueError(f"Workflow '{self.name}' has no steps")

        first_step = self.nodes[0]
        last_step = self.nodes[-1]

        return SubworkflowStep(
            workflow_id=self.name,
            input_model=first_step.input_model,
            output_model=last_step.output_model,
        )


class Registry:
    def __init__(self) -> None:
        self.steps: dict[str, Step[Any, Any]] = {}
        self.workflows: dict[str, Workflow] = {}

    def register_step(self, step: Step[Any, Any]) -> None:
        existing = self.steps.get(step.name)
        if existing is not None:
            if existing.fingerprint == step.fingerprint:
                return
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
        self._dependencies: set[str] = set()

    def __rshift__(self, other: Step[Any, Any] | Workflow) -> WorkflowBuilder:
        # Convert Workflow to SubworkflowStep if needed
        if isinstance(other, Workflow):
            step = other.to_subworkflow_step()
            # Track dependency
            self._dependencies.add(other.name)
        else:
            step = other

        if self.nodes:
            prev = self.nodes[-1]
            if prev.output_model is not step.input_model:
                raise TypeError(
                    f"Type mismatch: {prev.name} outputs {prev.output_model.__name__} "
                    f"but {step.name} expects {step.input_model.__name__}"
                )

        # Create new builder with updated nodes and preserve dependencies
        new_builder = WorkflowBuilder(self.name, self.nodes + [step])
        new_builder._dependencies = self._dependencies.copy()
        return new_builder

    def build(self) -> Workflow:
        if not self.nodes:
            raise ValueError("Workflow has no steps")
        wf = Workflow(self.name, self.nodes)
        # Transfer any tracked dependencies
        wf.dependencies = self._dependencies
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


def get_workflow_dependencies() -> dict[str, set[str]]:
    """Get all workflow dependencies as a mapping."""
    deps: dict[str, set[str]] = {}
    for wf in _REGISTRY.workflows.values():
        if wf.dependencies:
            deps[wf.name] = wf.dependencies
    return deps
