"""LLM provider protocol."""

from __future__ import annotations

from typing import Protocol


class LlmProvider(Protocol):
    backend: str
    model_name: str

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a text response."""
