"""Routing models for lightweight agentic workflows."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

RouteNode = Literal[
    "query_planner",
    "retrieval_strategist",
    "synthesizer",
    "citation_auditor",
    "finish",
]


class RouteDecision(TypedDict, total=False):
    next_node: RouteNode
    reason: str
    route_type: str
    should_continue: bool
    debug_signals: dict[str, Any]
