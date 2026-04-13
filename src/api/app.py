"""FastAPI application entrypoint."""

from fastapi import FastAPI

from src.api.routes.health import router as health_router
from src.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agentic RAG for Complex PDFs",
        version="0.1.0",
        debug=settings.debug,
    )
    app.include_router(health_router, prefix="/api")
    return app


app = create_app()

