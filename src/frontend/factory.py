"""Factory for frontend clients."""

from __future__ import annotations

from src.config.settings import Settings
from src.frontend.clients.base import QaClient
from src.frontend.clients.http_client import HttpQaClient
from src.frontend.clients.inprocess_client import InProcessQaClient
from src.generation.qa_service import QaService


def create_qa_client(settings: Settings) -> QaClient:
    mode = settings.frontend_backend_mode.strip().lower()
    if mode == "http":
        if not settings.frontend_api_base_url:
            raise ValueError(
                "FRONTEND_API_BASE_URL must be configured when FRONTEND_BACKEND_MODE=http."
            )
        return HttpQaClient(base_url=settings.frontend_api_base_url)
    if mode == "inprocess":
        return InProcessQaClient(qa_service=QaService.from_settings(settings))
    raise ValueError(f"Unsupported FRONTEND_BACKEND_MODE: {settings.frontend_backend_mode}")

