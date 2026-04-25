"""Lightweight query planner node."""

from __future__ import annotations

import logging
import re

from src.domain.models.state import ResearchState
from src.retrieval.signals import SearchSignals

logger = logging.getLogger(__name__)


class QueryPlannerNode:
    def run(self, state: ResearchState) -> ResearchState:
        raw_query = (
            state.get("resolved_user_query")
            or state.get("user_query")
            or state.get("normalized_query")
            or ""
        )
        normalized_query = self._normalize_query(raw_query)
        query_signature = SearchSignals.build_query_signature(normalized_query)
        request_options = state.get("request_options", {})
        conversation_constraints = state.get("conversation_constraints", {})
        last_planner_context = state.get("last_planner_context", {})
        effective_entities = self._resolve_effective_entities(
            state.get("current_entities", {}),
            conversation_constraints,
        )
        current_topic = self._resolve_current_topic(
            state.get("current_topic", {}),
            effective_entities,
            conversation_constraints,
        )

        state["normalized_query"] = normalized_query
        state["current_intent"] = self._infer_intent(normalized_query, query_signature)
        state["current_sub_intents"] = self._infer_sub_intents(
            normalized_query,
            query_signature,
            conversation_constraints,
        )
        state["current_entities"] = effective_entities
        state["current_topic"] = current_topic
        state["current_time_range"] = self._extract_time_range(
            normalized_query,
            conversation_constraints,
        )
        planner_constraints = self._resolve_planner_constraints(
            normalized_query,
            conversation_constraints,
            last_planner_context,
        )
        state["retrieval_plan"] = self._build_retrieval_plan(
            normalized_query=normalized_query,
            intent=state["current_intent"],
            query_signature=query_signature,
            time_range=state["current_time_range"],
            request_options=request_options,
            conversation_constraints=conversation_constraints,
            current_entities=effective_entities,
            current_topic=current_topic,
            planner_constraints=planner_constraints,
        )
        state["last_planner_context"] = {
            "intent": state["current_intent"],
            "metric_scope": planner_constraints["metric_scope"],
            "aspect_scope": planner_constraints["aspect_scope"],
            "comparison_target": planner_constraints["comparison_target"],
            "output_style": planner_constraints["output_style"],
            "entity_scope": list(state["retrieval_plan"].get("entity_scope", [])),
            "topic_scope": dict(state["retrieval_plan"].get("topic_scope", {})),
            "time_terms": list(state["retrieval_plan"].get("time_terms", [])),
        }
        state["next_action"] = "retrieval_strategist"
        logger.info(
            "planner.plan normalized_query=%r intent=%s sub_intents=%s entities=%s time_range=%s request_options=%s retrieval_plan=%s",
            state["normalized_query"],
            state["current_intent"],
            state["current_sub_intents"],
            state["current_entities"],
            state["current_time_range"],
            request_options,
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
        for old, new in replacements.items():
            query = query.replace(old, new)
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
    def _infer_sub_intents(
        normalized_query: str,
        query_signature,
        conversation_constraints: dict[str, object],
    ) -> list[str]:
        sub_intents: list[str] = []
        if query_signature.time_terms:
            sub_intents.append("time_grounded")
        elif conversation_constraints.get("inherited_time_terms"):
            sub_intents.append("time_inherited")
        if query_signature.prefers_structured_blocks:
            sub_intents.append("structured_preferred")
        if re.search(r"(多少|占比|比率|增长|同比|环比|数值|金额|规模)", normalized_query):
            sub_intents.append("fact_lookup")
        if re.search(r"(为什么|原因|影响|驱动|逻辑)", normalized_query):
            sub_intents.append("reasoning")
        if conversation_constraints.get("follow_up"):
            sub_intents.append("follow_up")
        return sub_intents

    @staticmethod
    def _extract_time_range(
        normalized_query: str,
        conversation_constraints: dict[str, object],
    ) -> dict[str, object]:
        raw_terms = re.findall(
            r"20\d{2}(?:Q[1-4]|q[1-4]|H[12]|h[12]|M\d{1,2}|m\d{1,2}|1-3Q|1-3q)?",
            normalized_query,
        )
        normalized_terms = [term.upper() for term in raw_terms]
        if not normalized_terms:
            inherited = conversation_constraints.get("inherited_time_terms", [])
            if isinstance(inherited, list):
                normalized_terms = [str(term).upper() for term in inherited]
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
        request_options: dict[str, object],
        conversation_constraints: dict[str, object],
        current_entities: dict[str, object],
        current_topic: dict[str, object],
        planner_constraints: dict[str, object],
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

        requested_top_k = request_options.get("top_k")
        if isinstance(requested_top_k, int) and requested_top_k > 0:
            top_k = requested_top_k

        requested_tables_only = request_options.get("tables_only")
        if isinstance(requested_tables_only, bool):
            prefers_tables = requested_tables_only

        return {
            "mode": "hybrid",
            "intent": intent,
            "complexity": complexity,
            "top_k": top_k,
            "tables_only": prefers_tables,
            "prefers_structured_blocks": query_signature.prefers_structured_blocks,
            "time_terms": list(time_range.get("raw_terms", [])),
            "entity_scope": list(current_entities.get("active_entities", [])),
            "topic_scope": dict(current_topic),
            "metric_scope": list(planner_constraints.get("metric_scope", [])),
            "aspect_scope": list(planner_constraints.get("aspect_scope", [])),
            "comparison_target": planner_constraints.get("comparison_target"),
            "output_style": planner_constraints.get("output_style"),
            "carry_over_constraints": {
                "follow_up": bool(conversation_constraints.get("follow_up")),
                "anchor_entity": conversation_constraints.get("anchor_entity"),
                "inherited_time_terms": list(conversation_constraints.get("inherited_time_terms", [])),
            },
        }

    @staticmethod
    def _estimate_complexity(normalized_query: str) -> str:
        if len(normalized_query) >= 30 or len(re.findall(r"[,、和及并且与]", normalized_query)) >= 2:
            return "high"
        if len(normalized_query) >= 16:
            return "medium"
        return "low"

    @staticmethod
    def _resolve_effective_entities(
        current_entities: dict[str, object],
        conversation_constraints: dict[str, object],
    ) -> dict[str, object]:
        result = dict(current_entities)
        active_entities: list[str] = []

        extracted = current_entities.get("current_query_entities")
        if isinstance(extracted, list):
            active_entities.extend(str(item) for item in extracted if str(item).strip())

        if not active_entities:
            anchor = conversation_constraints.get("anchor_entity")
            if anchor:
                active_entities.append(str(anchor))

        if active_entities:
            result["active_entities"] = active_entities
            result["last_entity"] = active_entities[0]
        else:
            result.setdefault("active_entities", [])
        return result

    @staticmethod
    def _resolve_current_topic(
        current_topic: dict[str, object],
        current_entities: dict[str, object],
        conversation_constraints: dict[str, object],
    ) -> dict[str, object]:
        result = dict(current_topic)
        normalized_subject = conversation_constraints.get("normalized_subject")
        if isinstance(normalized_subject, dict) and normalized_subject:
            result.update(normalized_subject)

        if not result.get("entity"):
            active_entities = current_entities.get("active_entities", [])
            if isinstance(active_entities, list) and active_entities:
                result["entity"] = active_entities[0]
        return result

    @staticmethod
    def _resolve_planner_constraints(
        normalized_query: str,
        conversation_constraints: dict[str, object],
        last_planner_context: dict[str, object],
    ) -> dict[str, object]:
        metric_scope = list(conversation_constraints.get("metric_hints", []))
        aspect_scope = list(conversation_constraints.get("aspect_hints", []))
        comparison_target = conversation_constraints.get("comparison_target")
        output_style_hints = list(conversation_constraints.get("output_style_hints", []))

        follow_up = bool(conversation_constraints.get("follow_up"))
        if follow_up and not metric_scope:
            metric_scope = list(last_planner_context.get("metric_scope", []))
        if follow_up and not aspect_scope:
            aspect_scope = list(last_planner_context.get("aspect_scope", []))
        if follow_up and not comparison_target:
            comparison_target = last_planner_context.get("comparison_target")

        output_style = output_style_hints[0] if output_style_hints else None
        if follow_up and not output_style:
            inherited_output_style = str(last_planner_context.get("output_style", "")).strip()
            output_style = inherited_output_style or None

        if "对比" in normalized_query or "比较" in normalized_query:
            aspect_scope = list(dict.fromkeys([*aspect_scope, "对比分析"]))

        return {
            "metric_scope": metric_scope,
            "aspect_scope": aspect_scope,
            "comparison_target": comparison_target,
            "output_style": output_style,
        }
