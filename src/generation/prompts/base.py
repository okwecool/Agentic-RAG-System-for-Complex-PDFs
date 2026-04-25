"""Base prompt template definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromptBundle:
    system_prompt: str
    user_prompt: str


class BasePromptTemplate:
    family = "base"

    def build(
        self,
        query: str,
        evidence: list[dict],
        conversation_context: dict | None = None,
    ) -> PromptBundle:
        raise NotImplementedError
