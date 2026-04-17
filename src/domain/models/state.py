"""Shared query state for multi-step workflows."""

from typing import Any, TypedDict

from src.domain.models.routing import RouteDecision


class ResearchState(TypedDict, total=False):
    thread_id: str
    user_query: str
    normalized_query: str
    workflow_status: str
    current_domain: str
    current_entities: dict[str, Any]
    current_time_range: dict[str, Any]
    current_intent: str
    current_sub_intents: list[str]
    request_options: dict[str, Any]
    retrieval_plan: dict[str, Any]
    route_decision: RouteDecision
    route_trace: list[dict[str, Any]]
    retrieved_candidates: list[dict[str, Any]]
    candidate_evidence_types: list[str]
    selected_evidence: list[dict[str, Any]]
    selected_evidence_types: list[str]
    draft_answer: str
    claims: list[dict[str, Any]]
    citation_map: list[dict[str, Any]]
    confidence: str
    model: str
    prompt_family: str
    embedding_backend: str
    next_action: str
    retry_count: int
    max_retry_count: int
    document_source_types: list[str]
    conversation_summary: str

