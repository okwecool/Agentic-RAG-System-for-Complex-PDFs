"""Citation auditor node backed by the existing audit module."""

from __future__ import annotations

from src.domain.models.state import ResearchState
from src.generation.citation_auditor import CitationAuditor


class CitationAuditorNode:
    def __init__(self, citation_auditor: CitationAuditor | None = None) -> None:
        self.citation_auditor = citation_auditor

    @classmethod
    def from_settings(cls) -> "CitationAuditorNode":
        return cls(citation_auditor=CitationAuditor())

    def run(self, state: ResearchState) -> ResearchState:
        if self.citation_auditor is None:
            state.setdefault(
                "citation_map",
                [{"claim": "placeholder claim", "chunk_ids": ["placeholder_chunk"]}],
            )
            state.setdefault("confidence", "medium")
            state.setdefault("workflow_status", "completed")
            return state

        claims = list(state.get("claims", []))
        evidence = list(state.get("selected_evidence", []))
        audit = self.citation_auditor.audit(claims=claims, evidence=evidence)
        state["citation_map"] = audit.get("citation_map") or audit.get("verified_claims", [])
        state["confidence"] = audit.get("final_confidence", state.get("confidence", "low"))
        state.setdefault("workflow_status", "completed")
        return state

