"""Lightweight explicit workflow for agentic query execution."""

from __future__ import annotations

from src.config.settings import Settings
from src.domain.models.state import ResearchState
from src.graph.nodes.citation_auditor import CitationAuditorNode
from src.graph.nodes.query_planner import QueryPlannerNode
from src.graph.nodes.retrieval_strategist import RetrievalStrategistNode
from src.graph.nodes.supervisor import SupervisorNode
from src.graph.nodes.synthesizer import SynthesizerNode
from src.graph.router import Router


class QueryWorkflow:
    def __init__(
        self,
        router: Router | None = None,
        supervisor: SupervisorNode | None = None,
        query_planner: QueryPlannerNode | None = None,
        retrieval_strategist: RetrievalStrategistNode | None = None,
        synthesizer: SynthesizerNode | None = None,
        citation_auditor: CitationAuditorNode | None = None,
        max_steps: int = 8,
    ) -> None:
        self.router = router or Router()
        self.supervisor = supervisor or SupervisorNode()
        self.query_planner = query_planner or QueryPlannerNode()
        self.retrieval_strategist = retrieval_strategist or RetrievalStrategistNode()
        self.synthesizer = synthesizer or SynthesizerNode()
        self.citation_auditor = citation_auditor or CitationAuditorNode()
        self.max_steps = max_steps

    @classmethod
    def from_settings(cls, settings: Settings, max_steps: int = 8) -> "QueryWorkflow":
        return cls(
            retrieval_strategist=RetrievalStrategistNode.from_settings(settings),
            max_steps=max_steps,
        )

    def run(self, initial_state: ResearchState) -> ResearchState:
        state = dict(initial_state)
        state.setdefault("workflow_status", "running")
        state.setdefault("retry_count", 0)
        state.setdefault("max_retry_count", 2)

        for _ in range(self.max_steps):
            decision = self.router.decide(state)
            self.supervisor.run(state, decision)

            next_node = decision["next_node"]
            if next_node == "finish" or not decision.get("should_continue", False):
                state["workflow_status"] = "completed"
                break
            if next_node == "query_planner":
                self.query_planner.run(state)
                continue
            if next_node == "retrieval_strategist":
                self.retrieval_strategist.run(state)
                continue
            if next_node == "synthesizer":
                self.synthesizer.run(state)
                continue
            if next_node == "citation_auditor":
                self.citation_auditor.run(state)
                continue

            state["workflow_status"] = "failed"
            break
        else:
            state["workflow_status"] = "max_steps_reached"

        return state

