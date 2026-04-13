"""Query planner node placeholder."""

from src.domain.models.state import ResearchState


class QueryPlannerNode:
    def run(self, state: ResearchState) -> ResearchState:
        state.setdefault("retrieval_plan", {})
        return state

