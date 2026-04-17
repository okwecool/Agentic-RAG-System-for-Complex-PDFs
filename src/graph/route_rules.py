"""Rule helpers for lightweight workflow routing."""

from __future__ import annotations

from src.domain.models.state import ResearchState


def get_retry_count(state: ResearchState) -> int:
    return int(state.get("retry_count", 0) or 0)


def get_max_retry_count(state: ResearchState) -> int:
    return int(state.get("max_retry_count", 2) or 2)


def has_plan(state: ResearchState) -> bool:
    if state.get("current_intent"):
        return True
    retrieval_plan = state.get("retrieval_plan") or {}
    required_keys = {"mode", "intent", "complexity"}
    return required_keys.issubset(retrieval_plan.keys())


def has_candidates(state: ResearchState) -> bool:
    return bool(state.get("retrieved_candidates"))


def has_selected_evidence(state: ResearchState) -> bool:
    return bool(state.get("selected_evidence"))


def has_draft_answer(state: ResearchState) -> bool:
    return bool((state.get("draft_answer") or "").strip())


def has_claims(state: ResearchState) -> bool:
    return bool(state.get("claims"))


def has_citation_map(state: ResearchState) -> bool:
    return bool(state.get("citation_map"))


def evidence_is_low_value_only(state: ResearchState) -> bool:
    evidence_types = list(state.get("selected_evidence_types", []))
    if not evidence_types:
        return False
    low_value_types = {
        "caption_evidence",
        "navigational_evidence",
        "metadata_evidence",
        "low_value_evidence",
    }
    return all(evidence_type in low_value_types for evidence_type in evidence_types)


def can_retry(state: ResearchState) -> bool:
    return get_retry_count(state) < get_max_retry_count(state)
