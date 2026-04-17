"""Query planner node placeholder."""

from src.domain.models.state import ResearchState


class QueryPlannerNode:
    def run(self, state: ResearchState) -> ResearchState:
        normalized_query = (state.get("user_query") or "").strip()
        if normalized_query and not state.get("normalized_query"):
            state["normalized_query"] = normalized_query
        state.setdefault("current_intent", "qa")
        state.setdefault("retrieval_plan", {})
        return state

