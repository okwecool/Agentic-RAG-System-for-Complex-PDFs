"""Client protocol for frontend-to-QA communication."""

from __future__ import annotations

from typing import Protocol


class QaClient(Protocol):
    def ask(
        self,
        query: str,
        top_k: int | None = None,
        tables_only: bool = False,
        session_id: str | None = None,
        qa_mode: str = "standard",
    ) -> dict: ...
