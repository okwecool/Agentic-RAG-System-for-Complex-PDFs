"""Lightweight query planner node."""

from __future__ import annotations

import logging
import re

from src.domain.models.state import ResearchState
from src.retrieval.signals import SearchSignals

logger = logging.getLogger(__name__)


class QueryPlannerNode:
    def run(self, state: ResearchState) -> ResearchState:
        raw_query = state.get("user_query") or state.get("normalized_query") or ""
        normalized_query = self._normalize_query(raw_query)
        query_signature = SearchSignals.build_query_signature(normalized_query)

        state["normalized_query"] = normalized_query
        state["current_intent"] = self._infer_intent(normalized_query, query_signature)
        state["current_sub_intents"] = self._infer_sub_intents(normalized_query, query_signature)
        state["current_time_range"] = self._extract_time_range(normalized_query)
        state["retrieval_plan"] = self._build_retrieval_plan(
            normalized_query=normalized_query,
            intent=state["current_intent"],
            query_signature=query_signature,
            time_range=state["current_time_range"],
        )
        state["next_action"] = "retrieval_strategist"
        logger.info(
            "planner.plan normalized_query=%r intent=%s sub_intents=%s time_range=%s retrieval_plan=%s",
            state["normalized_query"],
            state["current_intent"],
            state["current_sub_intents"],
            state["current_time_range"],
            state["retrieval_plan"],
        )
        return state

    @staticmethod
    def _normalize_query(query: str) -> str:
        query = " ".join(query.strip().split())
        replacements = {
            "？": "?",
            "！": "!",
            "，": ", ",
            "：": ": ",
            "；": "; ",
            "（": "(",
            "）": ")",
        }
        for src, target in replacements.items():
            query = query.replace(src, target)
        query = re.sub(r"\s+", " ", query).strip()
        return query

    @staticmethod
    def _infer_intent(normalized_query: str, query_signature) -> str:
        lowered = normalized_query.lower()
        structured_markers = ("图", "图表", "表", "table", "chart", "figure")
        compare_markers = ("对比", "比较", "区别", "vs", "versus")
        summary_markers = ("总结", "概述", "综述", "介绍", "有哪些", "信息")

        if any(marker in lowered for marker in compare_markers):
            return "compare"
        if any(marker in normalized_query for marker in summary_markers):
            return "summary"
        if query_signature.prefers_structured_blocks or any(marker in lowered for marker in structured_markers):
            return "structured_qa"
        return "qa"

    @staticmethod
    def _infer_sub_intents(normalized_query: str, query_signature) -> list[str]:
        sub_intents: list[str] = []
        if query_signature.time_terms:
            sub_intents.append("time_grounded")
        if query_signature.prefers_structured_blocks:
            sub_intents.append("structured_preferred")
        if re.search(r"(多少|占比|比例|增长|同比|环比|数值|金额|规模)", normalized_query):
            sub_intents.append("fact_lookup")
        if re.search(r"(为什么|原因|影响|驱动|逻辑)", normalized_query):
            sub_intents.append("reasoning")
        return sub_intents

    @staticmethod
    def _extract_time_range(normalized_query: str) -> dict[str, object]:
        raw_terms = re.findall(
            r"20\d{2}(?:Q[1-4]|q[1-4]|H[12]|h[12]|M\d{1,2}|m\d{1,2}|年Q1-3|q1-3|1-3Q|1-3q)?",
            normalized_query,
        )
        normalized_terms = [term.upper() for term in raw_terms]
        years = sorted({term[:4] for term in normalized_terms})
        return {
            "raw_terms": normalized_terms,
            "years": years,
            "is_time_bounded": bool(normalized_terms),
        }

    def _build_retrieval_plan(
        self,
        normalized_query: str,
        intent: str,
        query_signature,
        time_range: dict[str, object],
    ) -> dict[str, object]:
        complexity = self._estimate_complexity(normalized_query)
        prefers_tables = bool(
            query_signature.prefers_structured_blocks
            and re.search(r"(表|table|图表|chart|figure)", normalized_query.lower())
        )

        top_k = 4
        if complexity == "medium":
            top_k = 6
        elif complexity == "high":
            top_k = 8

        return {
            "mode": "hybrid",
            "intent": intent,
            "complexity": complexity,
            "top_k": top_k,
            "tables_only": prefers_tables,
            "prefers_structured_blocks": query_signature.prefers_structured_blocks,
            "time_terms": list(time_range.get("raw_terms", [])),
        }

    @staticmethod
    def _estimate_complexity(normalized_query: str) -> str:
        if len(normalized_query) >= 30 or len(re.findall(r"[,、和及并且以及]", normalized_query)) >= 2:
            return "high"
        if len(normalized_query) >= 16:
            return "medium"
        return "low"
