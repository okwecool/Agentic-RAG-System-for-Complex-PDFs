"""Citation auditor node placeholder."""

from src.domain.models.state import ResearchState


class CitationAuditorNode:
    def run(self, state: ResearchState) -> ResearchState:
        state.setdefault(
            "citation_map",
            [{"claim": "placeholder claim", "chunk_ids": ["placeholder_chunk"]}],
        )
        state.setdefault("workflow_status", "completed")
        return state

