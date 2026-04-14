"""Base helpers for LLM providers."""

from __future__ import annotations


class BaseLlmProvider:
    backend = "unknown"

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
