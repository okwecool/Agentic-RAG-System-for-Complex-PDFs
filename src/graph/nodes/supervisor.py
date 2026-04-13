"""Supervisor node placeholder."""

from src.domain.models.state import ResearchState


class SupervisorNode:
    def run(self, state: ResearchState) -> ResearchState:
        return state

