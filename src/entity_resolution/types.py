"""Shared types for entity resolution."""

from __future__ import annotations

from typing import TypedDict


class EntityMention(TypedDict, total=False):
    text: str
    canonical_name: str
    entity_type: str
    product: str
    confidence: float
    source: str


class EntityResolutionResult(TypedDict, total=False):
    mentions: list[EntityMention]
    query_entities: list[str]
    primary_entity: str
    topic: dict[str, str]
