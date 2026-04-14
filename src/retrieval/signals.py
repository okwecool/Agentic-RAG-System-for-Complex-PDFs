"""Generic retrieval signals and ranking helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


@dataclass(slots=True)
class QuerySignature:
    phrase: str
    terms: set[str]
    time_terms: set[str]
    prefers_structured_blocks: bool = False


@dataclass(slots=True)
class ChunkProfile:
    is_navigational: bool
    is_sparse: bool
    is_narrative: bool
    short_line_count: int
    digit_count: int


class SearchSignals:
    _QUERY_STOP_TERMS = {
        "什么",
        "如何",
        "多少",
        "哪些",
        "情况",
        "问题",
        "一下",
        "是否",
        "请问",
        "怎么",
        "怎样",
        "what",
        "how",
        "many",
        "much",
        "which",
        "does",
        "is",
        "are",
    }
    _NAVIGATION_MARKERS = (
        "目录",
        "图表目录",
        "contents",
        "table of contents",
        "figure index",
        "chart index",
        "appendix index",
    )
    _STRUCTURED_QUERY_MARKERS = (
        "图",
        "图表",
        "表",
        "table",
        "chart",
        "figure",
        "trend",
        "走势",
        "曲线",
    )

    @classmethod
    def normalize_text(cls, text: str) -> str:
        return " ".join(text.lower().split())

    @classmethod
    def text_signature(cls, text: str) -> str:
        normalized = cls.normalize_text(text)
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def build_query_signature(cls, query: str) -> QuerySignature:
        normalized = cls.normalize_text(query)
        phrase = normalized if len(normalized) >= 4 else ""
        latin_terms = set(re.findall(r"[a-z0-9]{2,}", normalized))
        cjk_terms = cls._extract_cjk_ngrams(normalized)
        term_candidates = latin_terms | cjk_terms
        time_terms = set(
            re.findall(r"20\d{2}(?:q[1-4]|h[12]|m\d{1,2}|年|q1-q3|1-3q)?", normalized)
        )
        terms = {term for term in term_candidates if term not in cls._QUERY_STOP_TERMS}
        prefers_structured_blocks = any(
            marker in normalized for marker in cls._STRUCTURED_QUERY_MARKERS
        )
        return QuerySignature(
            phrase=phrase,
            terms=terms,
            time_terms=time_terms,
            prefers_structured_blocks=prefers_structured_blocks,
        )

    @staticmethod
    def _extract_cjk_ngrams(text: str) -> set[str]:
        terms: set[str] = set()
        for match in re.findall(r"[\u4e00-\u9fff]{2,}", text):
            length = len(match)
            for n in (2, 3):
                if length < n:
                    continue
                for idx in range(length - n + 1):
                    terms.add(match[idx : idx + n])
            terms.add(match)
        return terms

    @classmethod
    def build_chunk_profile(cls, chunk) -> ChunkProfile:
        text = (chunk.text or "").strip()
        normalized = cls.normalize_text(" ".join(chunk.section_path + [text]))
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        digit_count = len(re.findall(r"\d", text))
        short_line_count = sum(1 for line in lines if len(line) <= 20)
        dotted_line_count = sum(1 for line in lines if line.count(".") >= 5)
        numeric_lines = sum(
            1 for line in lines if re.search(r"\d", line) and len(re.findall(r"\d", line)) >= 2
        )
        sentence_like_lines = sum(
            1 for line in lines if re.search(r"[。！？；:.]", line) or len(line) >= 24
        )
        is_navigational = any(marker in normalized for marker in cls._NAVIGATION_MARKERS)
        if dotted_line_count >= 1 and short_line_count >= 2:
            is_navigational = True
        is_sparse = False
        if lines:
            if digit_count >= 12 and short_line_count >= 3:
                is_sparse = True
            elif digit_count >= 12 and len(lines) >= 3 and short_line_count >= 2:
                is_sparse = True
            elif numeric_lines >= 3 and len(lines) >= 4:
                is_sparse = True
        is_narrative = bool(lines) and sentence_like_lines >= max(1, len(lines) // 2)
        return ChunkProfile(
            is_navigational=is_navigational,
            is_sparse=is_sparse,
            is_narrative=is_narrative,
            short_line_count=short_line_count,
            digit_count=digit_count,
        )

    @classmethod
    def relevance_adjustment(cls, chunk, query_signature: QuerySignature) -> float:
        if not query_signature.terms and not query_signature.time_terms:
            return 0.0

        haystack = cls.normalize_text(" ".join(chunk.section_path + [chunk.text[:280]]))
        bonus = 0.0
        term_hits = sum(1 for term in query_signature.terms if term in haystack)
        time_hits = sum(1 for term in query_signature.time_terms if term in haystack)

        if query_signature.phrase and query_signature.phrase in haystack:
            bonus += 0.012
        if term_hits:
            bonus += min(0.006 * term_hits, 0.018)
        if time_hits:
            bonus += min(0.008 * time_hits, 0.016)
        return bonus

    @classmethod
    def structural_adjustment(
        cls,
        chunk,
        query_signature: QuerySignature,
        profile: ChunkProfile | None = None,
    ) -> float:
        profile = profile or cls.build_chunk_profile(chunk)
        adjustment = 0.0
        if profile.is_navigational:
            adjustment -= 0.02
        if profile.is_sparse and not query_signature.prefers_structured_blocks:
            adjustment -= 0.03
        if profile.is_sparse and query_signature.prefers_structured_blocks:
            adjustment += 0.012
        if profile.is_narrative and not query_signature.prefers_structured_blocks:
            adjustment += 0.01
        return adjustment

    @classmethod
    def representative_rank_key(
        cls,
        item: dict,
        query_signature: QuerySignature | None = None,
    ) -> tuple[int, float, int]:
        chunk = item["chunk"]
        query_signature = query_signature or QuerySignature("", set(), set(), False)
        type_priority = {
            "paragraph": 3,
            "mixed": 3,
            "table": 2,
            "figure_caption": 2,
            "heading": 1,
        }.get(chunk.chunk_type, 0)
        text_length = len(chunk.text.strip())
        profile = cls.build_chunk_profile(chunk)
        score = float(item.get("score", 0.0))
        score += cls.relevance_adjustment(chunk, query_signature)
        score += cls.structural_adjustment(
            chunk,
            query_signature=query_signature,
            profile=profile,
        )
        return (type_priority, score, text_length)
