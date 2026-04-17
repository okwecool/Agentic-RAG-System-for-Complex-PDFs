"""In-process client that calls QaService directly."""

from __future__ import annotations

from src.generation.qa_service import QaService


class InProcessQaClient:
    def __init__(self, qa_service: QaService) -> None:
        self._qa_service = qa_service

    def ask(
        self,
        query: str,
        top_k: int | None = None,
        tables_only: bool = False,
        session_id: str | None = None,
    ) -> dict:
        return self._qa_service.answer(
            query=query,
            top_k=top_k,
            tables_only=tables_only,
        )

