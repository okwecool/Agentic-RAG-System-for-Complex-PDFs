"""Reranker provider protocol."""

from __future__ import annotations

from typing import Protocol


class RerankerProvider(Protocol):
    backend: str
    model_name: str

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """Return reranked candidates."""
