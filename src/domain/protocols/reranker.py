"""Reranker protocol."""

from typing import Any, Protocol


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Reorder retrieved candidates."""

