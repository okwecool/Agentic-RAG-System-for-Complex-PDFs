"""Supervisor node placeholder."""

from src.domain.models.routing import RouteDecision
from src.domain.models.state import ResearchState


class SupervisorNode:
    def run(self, state: ResearchState, decision: RouteDecision | None = None) -> ResearchState:
        state.setdefault("workflow_status", "running")
        if decision is not None:
            state["route_decision"] = decision
            state["next_action"] = decision["next_node"]
        return state

