"""Shared query state for multi-step workflows."""

from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    thread_id: str
    user_query: str
    normalized_query: str
    current_domain: str
    current_entities: dict[str, Any]
    current_time_range: dict[str, Any]
    current_intent: str
    retrieval_plan: dict[str, Any]
    retrieved_candidates: list[dict[str, Any]]
    selected_evidence: list[dict[str, Any]]
    draft_answer: str
    claims: list[dict[str, Any]]
    citation_map: list[dict[str, Any]]
    confidence: str
    next_action: str
    conversation_summary: str

