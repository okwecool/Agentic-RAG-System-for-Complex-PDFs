"""Rule-based entity resolver."""

from __future__ import annotations

import re

from src.entity_resolution.types import EntityMention, EntityResolutionResult


class RuleEntityResolver:
    _SUBJECT_NORMALIZATION_RULES = (
        (
            ("苹果手机", "iphone", "iPhone", "苹果 iPhone"),
            {
                "entity": "苹果",
                "product": "iPhone",
                "topic": "苹果手机",
            },
        ),
    )

    _STOPWORDS = {
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

    def resolve(
        self,
        query: str,
        messages: list[dict],
        current_entities: dict[str, object],
        current_topic: dict[str, object],
    ) -> EntityResolutionResult:
        normalized_subject = self._normalize_subject(query)
        if normalized_subject:
            mention: EntityMention = {
                "text": query,
                "canonical_name": normalized_subject["entity"],
                "entity_type": "company",
                "product": normalized_subject.get("product", ""),
                "confidence": 0.95,
                "source": "rule_alias",
            }
            return {
                "mentions": [mention],
                "query_entities": [normalized_subject["entity"]],
                "primary_entity": normalized_subject["entity"],
                "topic": dict(normalized_subject),
            }

        query_entities = self._extract_entities(query)
        primary_entity = query_entities[0] if query_entities else None

        topic: dict[str, str] = {}
        if current_topic.get("entity") and primary_entity == current_topic.get("entity"):
            topic = dict(current_topic)

        mentions: list[EntityMention] = [
            {
                "text": entity,
                "canonical_name": entity,
                "entity_type": "unknown",
                "confidence": 0.6,
                "source": "rule_token",
            }
            for entity in query_entities
        ]
        result: EntityResolutionResult = {
            "mentions": mentions,
            "query_entities": query_entities,
        }
        if primary_entity:
            result["primary_entity"] = primary_entity
        if topic:
            result["topic"] = topic
        return result

    @classmethod
    def _normalize_subject(cls, query: str) -> dict[str, str] | None:
        lowered = query.lower()
        for markers, normalized in cls._SUBJECT_NORMALIZATION_RULES:
            if any(marker.lower() in lowered for marker in markers):
                return dict(normalized)
        return None

    @classmethod
    def _extract_entities(cls, text: str) -> list[str]:
        candidates: list[str] = []
        for match in re.finditer(r"[\u4e00-\u9fffA-Za-z0-9]{2,32}", text):
            token = cls._trim_entity_candidate(match.group(0))
            if cls._looks_like_entity(token):
                candidates.append(token)

        deduped: list[str] = []
        seen: set[str] = set()
        for token in candidates:
            if token in seen:
                continue
            deduped.append(token)
            seen.add(token)
        return deduped

    @classmethod
    def _looks_like_entity(cls, token: str) -> bool:
        if not token:
            return False
        if token in cls._STOPWORDS:
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
            r"(近期|最近|今年|有哪些|有什么|怎么样|如何|发展势头|商业信息|情况|表现|呢).*$",
            "",
            token,
        )
        return token.strip()
