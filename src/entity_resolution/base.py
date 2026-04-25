"""Entity resolver protocol."""

from __future__ import annotations

from typing import Protocol

from src.entity_resolution.types import EntityResolutionResult


class EntityResolver(Protocol):
    def resolve(
        self,
        query: str,
        messages: list[dict],
        current_entities: dict[str, object],
        current_topic: dict[str, object],
    ) -> EntityResolutionResult: ...
