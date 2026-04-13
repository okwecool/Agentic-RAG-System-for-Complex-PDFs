"""Retrieval strategist node placeholder."""

from src.domain.models.state import ResearchState


class RetrievalStrategistNode:
    def run(self, state: ResearchState) -> ResearchState:
        state.setdefault("retrieved_candidates", [])
        return state

