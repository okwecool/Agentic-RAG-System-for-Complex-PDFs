"""No-op reranker."""

from __future__ import annotations

from src.retrieval.rerankers.base import BaseRerankerProvider


class NoOpReranker(BaseRerankerProvider):
    backend = "noop"

    def __init__(self) -> None:
        super().__init__(model_name="noop")

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        del query
        return candidates

    def describe(self) -> dict[str, str | int]:
        return {
            "backend": self.backend,
            "model_name": self.model_name,
        }
