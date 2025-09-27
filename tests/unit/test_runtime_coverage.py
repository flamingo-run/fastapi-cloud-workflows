"""Additional runtime tests to improve coverage."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi_cloudflow import Context, Step
from fastapi_cloudflow.core import get_registry
from fastapi_cloudflow.runtime import _build_step_router


class SimpleModel(BaseModel):
    value: int


def test_build_step_router_skips_native_steps():
    """Test that _build_step_router skips steps without functions (covers line 16)."""

    # Clear registry and add both callable and non-callable steps
    registry = get_registry()
    registry.steps.clear()

    # Add a callable step
    async def callable_step(ctx: Context, data: SimpleModel) -> SimpleModel:
        return data

    callable = Step(name="callable-step", input_model=SimpleModel, output_model=SimpleModel, fn=callable_step)
    registry.register_step(callable)

    # Add a non-callable step (like HttpStep or AssignStep)
    non_callable = Step(
        name="native-step",
        input_model=SimpleModel,
        output_model=SimpleModel,
        fn=None,  # This will cause it to be skipped
    )
    registry.register_step(non_callable)

    # Build router - should only include callable-step
    router = _build_step_router()

    # Check that only the callable step was added to routes
    # Note: routes include the /steps prefix from the router
    route_paths = [route.path for route in router.routes]
    assert "/steps/callable-step" in route_paths or "/callable-step" in route_paths
    assert "/steps/native-step" not in route_paths and "/native-step" not in route_paths


def test_registry_with_mixed_steps():
    """Test registry handling of mixed step types."""
    from fastapi_cloudflow import AssignStep, HttpStep

    # Clear registry
    registry = get_registry()
    registry.steps.clear()

    # Add various step types
    async def python_step(ctx: Context, data: SimpleModel) -> SimpleModel:
        return SimpleModel(value=data.value * 2)

    # Python step (callable)
    step1 = Step(name="python-step", input_model=SimpleModel, output_model=SimpleModel, fn=python_step)
    registry.register_step(step1)

    # HTTP step (non-callable)
    http_step = HttpStep(
        name="http-step",
        input_model=SimpleModel,
        output_model=SimpleModel,
        method="POST",
        url="https://api.example.com",
    )
    registry.register_step(http_step)

    # Assign step (non-callable)
    assign_step = AssignStep(
        name="assign-step", input_model=SimpleModel, output_model=SimpleModel, expr={"value": "${payload.value * 2}"}
    )
    registry.register_step(assign_step)

    # Build router
    router = _build_step_router()

    # Only the Python step should have a route
    route_paths = [route.path for route in router.routes]
    assert "/steps/python-step" in route_paths or "/python-step" in route_paths
    assert "/steps/http-step" not in route_paths and "/http-step" not in route_paths
    assert "/steps/assign-step" not in route_paths and "/assign-step" not in route_paths

    # Verify all steps are in registry
    assert len(registry.steps) == 3
    assert "python-step" in registry.steps
    assert "http-step" in registry.steps
    assert "assign-step" in registry.steps
