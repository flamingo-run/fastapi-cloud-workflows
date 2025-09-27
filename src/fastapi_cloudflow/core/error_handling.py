"""Error handling constructs for Cloud Workflows."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from fastapi_cloudflow.core.step import Step
from fastapi_cloudflow.core.workflow import WorkflowBuilder

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


class TryCatchStep(Step[InT, OutT]):
    """A step that wraps other steps with exception handling."""

    def __init__(
        self,
        name: str,
        input_model: type[InT],
        output_model: type[OutT],
        try_steps: list[Step[Any, Any]],
        except_steps: list[Step[Any, Any]] | None = None,
        error_var: str = "e",
        raise_on_error: bool = False,
    ) -> None:
        super().__init__(name=name, input_model=input_model, output_model=output_model, fn=None)
        self.try_steps = try_steps
        self.except_steps = except_steps or []
        self.error_var = error_var
        self.raise_on_error = raise_on_error


class TryCatchBuilder:
    """Builder for constructing try/catch blocks in workflows."""

    def __init__(self, name: str | None = None):
        self.name = name or "try_catch_block"
        self.try_builder: WorkflowBuilder | None = None
        self.except_builder: WorkflowBuilder | None = None
        self.error_var = "e"
        self.raise_on_error = False

    def try_block(self, builder: WorkflowBuilder) -> TryCatchBuilder:
        """Define the try block steps."""
        self.try_builder = builder
        return self

    def except_block(self, builder: WorkflowBuilder | None = None, error_var: str = "e") -> TryCatchBuilder:
        """Define the except block steps."""
        self.except_builder = builder
        self.error_var = error_var
        return self

    def raise_error(self, should_raise: bool = True) -> TryCatchBuilder:
        """Configure whether to re-raise the error after handling."""
        self.raise_on_error = should_raise
        return self

    def build(self) -> TryCatchStep[Any, Any]:
        """Build the try/catch step."""
        if not self.try_builder or not self.try_builder.nodes:
            raise ValueError("Try block must contain at least one step")

        # Get input/output models from the first and last steps
        first_step = self.try_builder.nodes[0]
        last_step = (
            self.try_builder.nodes[-1]
            if not self.except_builder
            else (self.except_builder.nodes[-1] if self.except_builder.nodes else self.try_builder.nodes[-1])
        )

        return TryCatchStep(
            name=self.name,
            input_model=first_step.input_model,
            output_model=last_step.output_model,
            try_steps=self.try_builder.nodes,
            except_steps=self.except_builder.nodes if self.except_builder else [],
            error_var=self.error_var,
            raise_on_error=self.raise_on_error,
        )


def try_catch(name: str | None = None) -> TryCatchBuilder:
    """Create a new try/catch block builder."""
    return TryCatchBuilder(name)
