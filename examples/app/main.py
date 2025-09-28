from fastapi import FastAPI

from examples.app.flows import (  # noqa: F401
    data_pipeline,
    echo_name,
    jokes,
    order,
    payments,
    post_story,
    resilient_payment,
    user,
)
from fastapi_cloudflow import attach_to_fastapi


def create_app() -> FastAPI:
    app = FastAPI()
    # Import types used for stub endpoints
    from examples.app.flows.payments import PSPReq, PSPRes
    from examples.app.flows.user import IdentityReq, IdentityRes

    @app.get("/health")
    def health() -> dict[str, str]:  # noqa: D401
        return {"status": "ok"}

    # Simple stubs so example HttpSteps resolve successfully during smoke tests
    @app.post("/signup", response_model=IdentityRes)
    def signup(req: IdentityReq) -> IdentityRes:
        return IdentityRes(external_id="u-0001", ok=True)

    @app.post("/charge", response_model=PSPRes)
    def charge(req: PSPReq) -> PSPRes:
        return PSPRes(status="approved", psp_id="p-0001")

    attach_to_fastapi(app)
    return app


app = create_app()
