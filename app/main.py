from __future__ import annotations

from fastapi import FastAPI

from fastapi_cloudflow import attach_to_fastapi


def create_app() -> FastAPI:
    app = FastAPI()
    attach_to_fastapi(app)  # auto-discover registered workflows
    return app


app = create_app()
