"""Placeholder local LLM provider for future deployment."""

from __future__ import annotations

from src.generation.providers.base import BaseLlmProvider


class LocalStubLlmProvider(BaseLlmProvider):
    backend = "local_stub"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError(
            "Local chat model provider is not implemented yet. "
            "Configure an OpenAI-compatible endpoint first."
        )
