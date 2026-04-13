"""Workflow placeholder."""

from src.domain.models.state import ResearchState


class QueryWorkflow:
    def run(self, initial_state: ResearchState) -> ResearchState:
        return initial_state

