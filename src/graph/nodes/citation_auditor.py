"""Citation auditor node backed by the existing audit module."""

from __future__ import annotations

import logging

from src.domain.models.state import ResearchState
from src.generation.citation_auditor import CitationAuditor

logger = logging.getLogger(__name__)


class CitationAuditorNode:
    def __init__(self, citation_auditor: CitationAuditor | None = None, strict: bool = False) -> None:
        self.citation_auditor = citation_auditor
        self.strict = strict

    @classmethod
    def from_settings(cls) -> "CitationAuditorNode":
        return cls(citation_auditor=CitationAuditor(), strict=True)

    def run(self, state: ResearchState) -> ResearchState:
        if self.citation_auditor is None:
            if self.strict:
                raise RuntimeError("CitationAuditorNode requires a CitationAuditor in strict mode.")
            state.setdefault(
                "citation_map",
                [{"claim": "placeholder claim", "chunk_ids": ["placeholder_chunk"]}],
            )
            state.setdefault("confidence", "medium")
            state.setdefault("workflow_status", "completed")
            logger.info(
                "auditor.placeholder claims=%s citation_map=%s confidence=%s",
                len(state.get("claims", [])),
                len(state.get("citation_map", [])),
                state.get("confidence"),
            )
            return state

        claims = list(state.get("claims", []))
        evidence = list(state.get("selected_evidence", []))
        logger.info(
            "auditor.start claims=%s evidence=%s",
            len(claims),
            len(evidence),
        )
        audit = self.citation_auditor.audit(claims=claims, evidence=evidence)
        state["citation_map"] = audit.get("citation_map") or audit.get("verified_claims", [])
        state["confidence"] = audit.get("final_confidence", state.get("confidence", "low"))
        state.setdefault("workflow_status", "completed")
        logger.info(
            "auditor.result citation_map=%s confidence=%s unsupported_claims=%s",
            len(state.get("citation_map", [])),
            state.get("confidence"),
            len(audit.get("unsupported_claims", [])),
        )
        return state

