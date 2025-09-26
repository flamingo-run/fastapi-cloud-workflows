"""Subworkflow support for Cloud Workflows."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from fastapi_cloudflow.core.step import Step

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


class SubworkflowStep[InT: BaseModel, OutT: BaseModel](Step[InT, OutT]):
    """
    A step that executes another workflow.

    This step represents a call to another Cloud Workflow, enabling
    workflow composition and reusability.
    """

    def __init__(
        self,
        workflow_id: str,
        input_model: type[InT],
        output_model: type[OutT],
        wait: bool = True,
        input_mapping: dict[str, Any] | None = None,
        output_mapping: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize a subworkflow step.

        Args:
            workflow_id: The ID of the workflow to call
            input_model: The input model type for this step
            output_model: The output model type for this step
            wait: Whether to wait for the subworkflow to complete (default: True)
            input_mapping: Optional mapping for input parameters
            output_mapping: Optional mapping for output results
        """
        super().__init__(
            name=f"call_{workflow_id.replace('-', '_')}",
            input_model=input_model,
            output_model=output_model,
            fn=None,  # Subworkflows are not callable locally
        )
        self.workflow_id = workflow_id
        self.wait = wait
        self.input_mapping = input_mapping or {}
        self.output_mapping = output_mapping or {}
