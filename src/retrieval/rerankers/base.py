"""Base reranker provider."""

from __future__ import annotations


class BaseRerankerProvider:
    backend = "base"

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
