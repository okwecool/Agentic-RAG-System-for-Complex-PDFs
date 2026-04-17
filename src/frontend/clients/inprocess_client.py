"""In-process client that calls QA services directly."""

from __future__ import annotations

from src.generation.agentic_qa_service import AgenticQaService
from src.generation.qa_service import QaService


class InProcessQaClient:
    def __init__(
        self,
        qa_service: QaService,
        agentic_qa_service: AgenticQaService | None = None,
    ) -> None:
        self._qa_service = qa_service
        self._agentic_qa_service = agentic_qa_service

    def ask(
        self,
        query: str,
        top_k: int | None = None,
        tables_only: bool = False,
        session_id: str | None = None,
        qa_mode: str = "standard",
    ) -> dict:
        if qa_mode == "agentic":
            if self._agentic_qa_service is None:
                raise RuntimeError("Agentic QA service is not available.")
            return self._agentic_qa_service.answer(
                query=query,
                top_k=top_k,
                tables_only=tables_only,
            )

        return self._qa_service.answer(
            query=query,
            top_k=top_k,
            tables_only=tables_only,
        )
