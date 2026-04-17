"""Conversation-aware query resolution node."""

from __future__ import annotations

import logging
import re

from src.domain.models.state import ResearchState

logger = logging.getLogger(__name__)


class ConversationResolverNode:
    def run(self, state: ResearchState) -> ResearchState:
        raw_query = (state.get("user_query") or "").strip()
        messages = list(state.get("messages", []))
        anchor_entity = self._resolve_anchor_entity(state, messages)

        resolved_query = raw_query
        if raw_query and self._needs_resolution(raw_query) and anchor_entity:
            resolved_query = self._inject_anchor_entity(raw_query, anchor_entity)

        current_entities = dict(state.get("current_entities", {}))
        current_entities["conversation_anchor"] = anchor_entity
        current_entities["current_query_entities"] = self._extract_entities(raw_query)
        state["current_entities"] = current_entities
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

    @staticmethod
    def _needs_resolution(query: str) -> bool:
        contextual_markers = (
            "那",
            "那么",
            "它",
            "他",
            "她",
            "这家",
            "该公司",
            "这家公司",
            "其",
            "今年",
            "近期",
            "最近",
        )
        if any(marker in query for marker in contextual_markers):
            return True
        return not bool(ConversationResolverNode._extract_entities(query))

    @staticmethod
    def _inject_anchor_entity(query: str, anchor_entity: str) -> str:
        leading_tokens = (
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
        )
        for token in leading_tokens:
            if query.startswith(token):
                return f"{anchor_entity}{query[len(token):]}"
        return f"{anchor_entity}{query}"

    @staticmethod
    def _resolve_anchor_entity(state: ResearchState, messages: list[dict]) -> str | None:
        current_entities = state.get("current_entities", {})
        anchor = current_entities.get("last_entity") or current_entities.get("conversation_anchor")
        if anchor:
            return str(anchor)

        for item in reversed(messages):
            entities = ConversationResolverNode._extract_entities(str(item.get("content", "")))
            if entities:
                return entities[0]
        return None

    @staticmethod
    def _extract_entities(text: str) -> list[str]:
        candidates: list[str] = []
        for match in re.finditer(r"[\u4e00-\u9fffA-Za-z0-9]{2,32}", text):
            token = ConversationResolverNode._trim_entity_candidate(match.group(0))
            if ConversationResolverNode._looks_like_entity(token):
                candidates.append(token)

        deduped: list[str] = []
        seen: set[str] = set()
        for token in candidates:
            if token in seen:
                continue
            deduped.append(token)
            seen.add(token)
        return deduped

    @staticmethod
    def _looks_like_entity(token: str) -> bool:
        stopwords = {
            "近期",
            "最近",
            "发展",
            "势头",
            "如何",
            "今年",
            "哪些",
            "商业信息",
            "问题",
            "提问",
            "总结",
            "公司",
            "行业",
            "测试问题",
        }
        if not token:
            return False
        if token in stopwords:
            return False
        if token.isdigit():
            return False
        if len(token) <= 1:
            return False
        if re.fullmatch(r"20\d{2}", token):
            return False
        return True

    @staticmethod
    def _trim_entity_candidate(token: str) -> str:
        token = re.sub(r"^(关于|请问|那么|那|这个|这家|该)", "", token)
        token = re.sub(
            r"(近期|最近|今年|有哪些|有什么|怎么样|如何|发展势头|商业信息|情况|表现|呢|吗).*$",
            "",
            token,
        )
        return token.strip()
