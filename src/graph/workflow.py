"""Lightweight explicit workflow for agentic query execution."""

from __future__ import annotations

import logging

from src.config.settings import Settings
from src.domain.models.state import ResearchState
from src.graph.nodes.citation_auditor import CitationAuditorNode
from src.graph.nodes.conversation_resolver import ConversationResolverNode
from src.graph.nodes.query_planner import QueryPlannerNode
from src.graph.nodes.retrieval_strategist import RetrievalStrategistNode
from src.graph.nodes.supervisor import SupervisorNode
from src.graph.nodes.synthesizer import SynthesizerNode
from src.graph.router import Router

logger = logging.getLogger(__name__)


class QueryWorkflow:
    def __init__(
        self,
        router: Router | None = None,
        supervisor: SupervisorNode | None = None,
        conversation_resolver: ConversationResolverNode | None = None,
        query_planner: QueryPlannerNode | None = None,
        retrieval_strategist: RetrievalStrategistNode | None = None,
        synthesizer: SynthesizerNode | None = None,
        citation_auditor: CitationAuditorNode | None = None,
        max_steps: int = 8,
    ) -> None:
        self.router = router or Router()
        self.supervisor = supervisor or SupervisorNode()
        self.conversation_resolver = conversation_resolver or ConversationResolverNode()
        self.query_planner = query_planner or QueryPlannerNode()
        self.retrieval_strategist = retrieval_strategist or RetrievalStrategistNode()
        self.synthesizer = synthesizer or SynthesizerNode()
        self.citation_auditor = citation_auditor or CitationAuditorNode()
        self.max_steps = max_steps

    @classmethod
    def from_settings(cls, settings: Settings, max_steps: int = 8) -> "QueryWorkflow":
        return cls(
            retrieval_strategist=RetrievalStrategistNode.from_settings(settings),
            synthesizer=SynthesizerNode.from_settings(settings),
            citation_auditor=CitationAuditorNode.from_settings(),
            max_steps=max_steps,
        )

    def run(self, initial_state: ResearchState) -> ResearchState:
        state = dict(initial_state)
        state.setdefault("workflow_status", "running")
        state.setdefault("retry_count", 0)
        state.setdefault("max_retry_count", 2)
        state.setdefault("route_trace", [])
        logger.info(
            "workflow.start query=%r max_steps=%s initial_retry_count=%s",
            state.get("user_query"),
            self.max_steps,
            state.get("retry_count"),
        )

        for step_index in range(1, self.max_steps + 1):
            decision = self.router.decide(state)
            self.supervisor.run(state, decision)
            logger.info(
                "workflow.step index=%s next_node=%s reason=%s route_type=%s",
                step_index,
                decision["next_node"],
                decision.get("reason"),
                decision.get("route_type"),
            )
            trace_entry = {
                "step": step_index,
                "next_node": decision["next_node"],
                "reason": decision.get("reason"),
                "route_type": decision.get("route_type"),
                "debug_signals": dict(decision.get("debug_signals", {})),
            }

            next_node = decision["next_node"]
            if next_node == "finish" or not decision.get("should_continue", False):
                state["workflow_status"] = "completed"
                trace_entry["node_summary"] = {
                    "workflow_status": state["workflow_status"],
                    "retry_count": state.get("retry_count", 0),
                }
                state["route_trace"].append(trace_entry)
                logger.info(
                    "workflow.finish status=%s route_type=%s retry_count=%s trace_len=%s",
                    state["workflow_status"],
                    decision.get("route_type"),
                    state.get("retry_count"),
                    len(state.get("route_trace", [])),
                )
                break
            if next_node == "conversation_resolver":
                self.conversation_resolver.run(state)
                trace_entry["node_summary"] = self._summarize_conversation_resolution(state)
                state["route_trace"].append(trace_entry)
                continue
            if next_node == "query_planner":
                self.query_planner.run(state)
                trace_entry["node_summary"] = self._summarize_planner(state)
                state["route_trace"].append(trace_entry)
                continue
            if next_node == "retrieval_strategist":
                self.retrieval_strategist.run(state)
                trace_entry["node_summary"] = self._summarize_retrieval(state)
                state["route_trace"].append(trace_entry)
                continue
            if next_node == "synthesizer":
                self.synthesizer.run(state)
                trace_entry["node_summary"] = self._summarize_synthesizer(state)
                state["route_trace"].append(trace_entry)
                continue
            if next_node == "citation_auditor":
                self.citation_auditor.run(state)
                trace_entry["node_summary"] = self._summarize_auditor(state)
                state["route_trace"].append(trace_entry)
                continue

            state["workflow_status"] = "failed"
            trace_entry["node_summary"] = {
                "workflow_status": state["workflow_status"],
                "error": "unknown_next_node",
            }
            state["route_trace"].append(trace_entry)
            logger.warning(
                "workflow.failed unknown_next_node=%s",
                next_node,
            )
            break
        else:
            state["workflow_status"] = "max_steps_reached"
            logger.warning(
                "workflow.max_steps_reached query=%r retry_count=%s",
                state.get("user_query"),
                state.get("retry_count"),
            )

        return state

    @staticmethod
    def _summarize_planner(state: ResearchState) -> dict:
        retrieval_plan = state.get("retrieval_plan", {})
        return {
            "intent": state.get("current_intent"),
            "sub_intents": list(state.get("current_sub_intents", [])),
            "top_k": retrieval_plan.get("top_k"),
            "tables_only": retrieval_plan.get("tables_only"),
            "time_terms": list(retrieval_plan.get("time_terms", [])),
        }

    @staticmethod
    def _summarize_conversation_resolution(state: ResearchState) -> dict:
        current_entities = state.get("current_entities", {})
        return {
            "resolved_user_query": state.get("resolved_user_query"),
            "conversation_anchor": current_entities.get("conversation_anchor"),
            "message_count": len(state.get("messages", [])),
        }

    @staticmethod
    def _summarize_retrieval(state: ResearchState) -> dict:
        return {
            "retrieved_count": len(state.get("retrieved_candidates", [])),
            "selected_count": len(state.get("selected_evidence", [])),
            "selected_evidence_types": list(state.get("selected_evidence_types", [])),
            "document_source_types": list(state.get("document_source_types", [])),
            "embedding_backend": state.get("embedding_backend"),
        }

    @staticmethod
    def _summarize_synthesizer(state: ResearchState) -> dict:
        return {
            "answer_len": len(state.get("draft_answer", "")),
            "claim_count": len(state.get("claims", [])),
            "confidence": state.get("confidence"),
            "model": state.get("model"),
            "prompt_family": state.get("prompt_family"),
        }

    @staticmethod
    def _summarize_auditor(state: ResearchState) -> dict:
        return {
            "citation_count": len(state.get("citation_map", [])),
            "confidence": state.get("confidence"),
            "workflow_status": state.get("workflow_status"),
        }

