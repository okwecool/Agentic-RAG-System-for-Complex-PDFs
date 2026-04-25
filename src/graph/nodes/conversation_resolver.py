"""Conversation-aware query resolution node."""

from __future__ import annotations

import logging
import re

from src.domain.models.state import ResearchState
from src.entity_resolution import RuleEntityResolver
from src.entity_resolution.base import EntityResolver

logger = logging.getLogger(__name__)


class ConversationResolverNode:
    _CONTEXTUAL_MARKERS = (
        "那它",
        "那他",
        "那她",
        "那么它",
        "那么他",
        "那么她",
        "这个",
        "这家",
        "这家公司",
        "该公司",
        "它",
        "他",
        "她",
        "其",
        "今年",
        "近期",
        "最近",
    )

    _LEADING_TOKENS = (
        "那么它",
        "那么他",
        "那么她",
        "那它",
        "那他",
        "那她",
        "那么",
        "那",
        "它",
        "他",
        "她",
        "其",
        "这家公司",
        "该公司",
        "这家",
        "这个",
    )

    _METRIC_MARKERS = {
        "销量": ("销量",),
        "营收": ("营收", "收入"),
        "利润": ("利润", "净利润", "盈利"),
        "份额": ("份额", "市占率", "占比"),
        "增长": ("增长", "同比", "环比", "增速"),
    }

    _ASPECT_MARKERS = {
        "近期表现": ("近期", "最近", "势头", "表现"),
        "财务表现": ("财报", "业绩", "营收", "利润"),
        "产品表现": ("产品", "机型", "系列"),
    }

    _OUTPUT_STYLE_MARKERS = {
        "brief": ("简单说", "一句话", "简要", "简单总结"),
        "detailed": ("详细", "展开", "具体说说", "详细说"),
        "list": ("列一下", "有哪些", "列个表"),
    }

    def __init__(self, entity_resolver: EntityResolver | None = None) -> None:
        self.entity_resolver = entity_resolver or RuleEntityResolver()

    def run(self, state: ResearchState) -> ResearchState:
        raw_query = (state.get("user_query") or "").strip()
        messages = list(state.get("messages", []))
        resolution = self.entity_resolver.resolve(
            query=raw_query,
            messages=messages,
            current_entities=dict(state.get("current_entities", {})),
            current_topic=dict(state.get("current_topic", {})),
        )

        anchor_entity = resolution.get("primary_entity") or self._resolve_anchor_entity(
            state=state,
            messages=messages,
        )
        current_query_entities = list(resolution.get("query_entities", []))
        normalized_subject = dict(resolution.get("topic", {}) or {})
        if self._starts_with_context_marker(raw_query):
            current_query_entities = []
            if not normalized_subject:
                anchor_entity = self._resolve_anchor_entity(state=state, messages=messages)

        inherited_time_terms = self._extract_recent_time_terms(messages)
        metric_hints = self._extract_metric_hints(raw_query)
        aspect_hints = self._extract_aspect_hints(raw_query)
        comparison_target = self._extract_comparison_target(raw_query, anchor_entity)
        output_style_hints = self._extract_output_style_hints(raw_query)

        resolved_query = raw_query
        if raw_query and not normalized_subject and self._needs_resolution(raw_query, current_query_entities) and anchor_entity:
            resolved_query = self._inject_anchor_entity(raw_query, anchor_entity)

        current_entities = dict(state.get("current_entities", {}))
        current_entities["conversation_anchor"] = anchor_entity
        current_entities["current_query_entities"] = current_query_entities
        if anchor_entity:
            current_entities["last_entity"] = anchor_entity
        topic_product = normalized_subject.get("product")
        if topic_product:
            current_entities["last_product"] = topic_product
        state["current_entities"] = current_entities

        if normalized_subject:
            state["current_topic"] = normalized_subject

        state["conversation_constraints"] = {
            "follow_up": bool(anchor_entity and self._needs_resolution(raw_query, current_query_entities)),
            "anchor_entity": anchor_entity,
            "current_query_entities": list(current_query_entities),
            "normalized_subject": dict(normalized_subject),
            "inherited_time_terms": inherited_time_terms,
            "metric_hints": metric_hints,
            "aspect_hints": aspect_hints,
            "comparison_target": comparison_target,
            "output_style_hints": output_style_hints,
            "message_count": len(messages),
        }
        state["resolved_user_query"] = resolved_query
        state["next_action"] = "query_planner"

        logger.info(
            "conversation.resolve raw_query=%r resolved_query=%r anchor_entity=%r message_count=%s",
            raw_query,
            resolved_query,
            anchor_entity,
            len(messages),
        )
        return state

    @classmethod
    def _needs_resolution(cls, query: str, query_entities: list[str]) -> bool:
        if any(marker in query for marker in cls._CONTEXTUAL_MARKERS):
            return True
        return not bool(query_entities)

    @classmethod
    def _starts_with_context_marker(cls, query: str) -> bool:
        return any(query.startswith(token) for token in cls._LEADING_TOKENS)

    @classmethod
    def _inject_anchor_entity(cls, query: str, anchor_entity: str) -> str:
        for token in cls._LEADING_TOKENS:
            if query.startswith(token):
                return f"{anchor_entity}{query[len(token):]}"
        return f"{anchor_entity}{query}"

    @staticmethod
    def _resolve_anchor_entity(
        state: ResearchState,
        messages: list[dict],
    ) -> str | None:
        current_entities = state.get("current_entities", {})
        anchor = current_entities.get("last_entity") or current_entities.get("conversation_anchor")
        if anchor:
            return str(anchor)

        fallback_resolver = RuleEntityResolver()
        for item in reversed(messages):
            resolution = fallback_resolver.resolve(
                query=str(item.get("content", "")),
                messages=[],
                current_entities={},
                current_topic={},
            )
            if resolution.get("primary_entity"):
                return str(resolution["primary_entity"])
        return None

    @staticmethod
    def _extract_recent_time_terms(messages: list[dict]) -> list[str]:
        terms: list[str] = []
        seen: set[str] = set()
        for item in reversed(messages[-6:]):
            content = str(item.get("content", ""))
            for term in re.findall(r"20\d{2}(?:Q[1-4]|q[1-4]|H[12]|h[12])?", content):
                normalized = term.upper()
                if normalized in seen:
                    continue
                seen.add(normalized)
                terms.append(normalized)
        return terms

    @classmethod
    def _extract_metric_hints(cls, query: str) -> list[str]:
        hints: list[str] = []
        lowered = query.lower()
        for label, markers in cls._METRIC_MARKERS.items():
            if any(marker.lower() in lowered for marker in markers):
                hints.append(label)
        return hints

    @classmethod
    def _extract_aspect_hints(cls, query: str) -> list[str]:
        hints: list[str] = []
        lowered = query.lower()
        for label, markers in cls._ASPECT_MARKERS.items():
            if any(marker.lower() in lowered for marker in markers):
                hints.append(label)
        return hints

    @staticmethod
    def _extract_comparison_target(query: str, anchor_entity: str | None) -> str | None:
        match = re.search(r"(?:和|与)([\u4e00-\u9fffA-Za-z0-9]{2,32})(?:比|相比|对比)", query)
        if match:
            target = match.group(1).strip()
            if target and target != anchor_entity:
                return target
        return None

    @classmethod
    def _extract_output_style_hints(cls, query: str) -> list[str]:
        hints: list[str] = []
        lowered = query.lower()
        for label, markers in cls._OUTPUT_STYLE_MARKERS.items():
            if any(marker.lower() in lowered for marker in markers):
                hints.append(label)
        return hints
