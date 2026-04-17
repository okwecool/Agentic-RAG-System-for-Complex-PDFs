"""Lightweight explicit router for agentic workflows."""

from __future__ import annotations

import logging

from src.domain.models.routing import RouteDecision
from src.domain.models.state import ResearchState
from src.graph import route_rules

logger = logging.getLogger(__name__)


class Router:
    def decide(self, state: ResearchState) -> RouteDecision:
        debug_signals = {
            "has_plan": route_rules.has_plan(state),
            "has_candidates": route_rules.has_candidates(state),
            "has_selected_evidence": route_rules.has_selected_evidence(state),
            "has_draft_answer": route_rules.has_draft_answer(state),
            "has_claims": route_rules.has_claims(state),
            "has_citation_map": route_rules.has_citation_map(state),
            "retry_count": route_rules.get_retry_count(state),
            "max_retry_count": route_rules.get_max_retry_count(state),
            "selected_evidence_types": list(state.get("selected_evidence_types", [])),
        }

        if not route_rules.has_plan(state):
            decision = {
                "next_node": "query_planner",
                "reason": "missing_plan",
                "route_type": "plan_then_retrieve",
                "should_continue": True,
                "debug_signals": debug_signals,
            }
            logger.info(
                "router.decide next_node=%s reason=%s route_type=%s signals=%s",
                decision["next_node"],
                decision["reason"],
                decision["route_type"],
                debug_signals,
            )
            return decision

        if not route_rules.has_candidates(state):
            decision = {
                "next_node": "retrieval_strategist",
                "reason": "missing_candidates",
                "route_type": "retrieve_then_synthesize",
                "should_continue": True,
                "debug_signals": debug_signals,
            }
            logger.info(
                "router.decide next_node=%s reason=%s route_type=%s signals=%s",
                decision["next_node"],
                decision["reason"],
                decision["route_type"],
                debug_signals,
            )
            return decision

        if (
            not route_rules.has_selected_evidence(state)
            or route_rules.evidence_is_low_value_only(state)
        ):
            if route_rules.can_retry(state):
                decision = {
                    "next_node": "retrieval_strategist",
                    "reason": "insufficient_evidence",
                    "route_type": "refine_retrieve",
                    "should_continue": True,
                    "debug_signals": debug_signals,
                }
                logger.info(
                    "router.decide next_node=%s reason=%s route_type=%s signals=%s",
                    decision["next_node"],
                    decision["reason"],
                    decision["route_type"],
                    debug_signals,
                )
                return decision

        if not route_rules.has_draft_answer(state):
            decision = {
                "next_node": "synthesizer",
                "reason": "ready_to_synthesize",
                "route_type": "synthesize",
                "should_continue": True,
                "debug_signals": debug_signals,
            }
            logger.info(
                "router.decide next_node=%s reason=%s route_type=%s signals=%s",
                decision["next_node"],
                decision["reason"],
                decision["route_type"],
                debug_signals,
            )
            return decision

        if not route_rules.has_citation_map(state):
            decision = {
                "next_node": "citation_auditor",
                "reason": "missing_citation_audit",
                "route_type": "audit",
                "should_continue": True,
                "debug_signals": debug_signals,
            }
            logger.info(
                "router.decide next_node=%s reason=%s route_type=%s signals=%s",
                decision["next_node"],
                decision["reason"],
                decision["route_type"],
                debug_signals,
            )
            return decision

        decision = {
            "next_node": "finish",
            "reason": "workflow_complete",
            "route_type": "finish",
            "should_continue": False,
            "debug_signals": debug_signals,
        }
        logger.info(
            "router.decide next_node=%s reason=%s route_type=%s signals=%s",
            decision["next_node"],
            decision["reason"],
            decision["route_type"],
            debug_signals,
        )
        return decision
