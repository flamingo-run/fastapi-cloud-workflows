import uuid
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response

from .core import Context, Step, WorkflowMeta, get_registry


def _build_step_router() -> APIRouter:
    router = APIRouter(prefix="/steps")
    registry = get_registry()
    for step in registry.steps.values():
        if step.fn is None:
            continue

        def make_handler(s: Step[Any, Any]):
            async def handler(request: Request, response: Response) -> Any:
                ctx: Context = request.state.context
                ctx.workflow.step = s.name
                payload_dict = await request.json()
                body = s.input_model.model_validate(payload_dict)  # type: ignore[attr-defined]
                result = await s.fn(ctx, body)  # type: ignore[call-arg]
                response.headers["X-Workflow-Run-Id"] = ctx.workflow.run_id or ""
                return result

            return handler

        router.add_api_route(
            f"/{step.name}",
            endpoint=make_handler(step),
            methods=["POST"],
            response_model=step.output_model,
        )
    return router


def attach_to_fastapi(app: FastAPI) -> None:
    @app.middleware("http")
    async def inject_context(request: Request, call_next):
        run_id = request.headers.get("X-Workflow-Run-Id") or str(uuid.uuid4())
        name = request.headers.get("X-Workflow-Name")
        ctx = Context(request=request, workflow=WorkflowMeta(name=name, step=None, run_id=run_id))
        request.state.context = ctx
        return await call_next(request)

    app.include_router(_build_step_router())


def build_app() -> FastAPI:
    app = FastAPI()
    attach_to_fastapi(app)
    return app
