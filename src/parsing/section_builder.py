"""Section path construction helpers."""

import re

from src.domain.models.document import Block, Document


class SectionBuilder:
    STRUCTURED_HEADING_PATTERN = re.compile(
        r"^("
        r"\d{1,2}(?:\.\d+){0,3}"
        r"|[IVXLC]+[.)]?"
        r"|[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343]+[、.)．]?"
        r")\s*.+"
    )

    def apply(self, document: Document) -> Document:
        current_section = ["Document"]
        for page in document.pages:
            for block in page.blocks:
                if self._should_start_section(block):
                    heading = self._normalize_heading(block.text)
                    level = self._infer_level(heading)
                    current_section = current_section[: level - 1]
                    current_section.append(heading)
                if not block.section_path:
                    block.section_path = current_section.copy()
        return document

    @staticmethod
    def _normalize_heading(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def _infer_level(heading: str) -> int:
        match = re.match(r"^(\d+(?:\.\d+)*)", heading)
        if match:
            return min(len(match.group(1).split(".")), 6)
        return 1

    def _should_start_section(self, block: Block) -> bool:
        if block.type != "heading" or not block.text.strip():
            return False

        heading = self._normalize_heading(block.text)
        if not heading:
            return False
        if self._looks_like_source_or_footer_heading(heading):
            return False
        if self._looks_like_date_or_period_heading(heading):
            return False
        if self._looks_like_page_label(heading):
            return False

        page_profile = (block.source_span or {}).get("page_profile")
        if page_profile == "label_dense":
            return False

        if self._looks_like_structured_heading(heading):
            return True

        if len(heading) <= 4:
            return False
        return True

    def _looks_like_structured_heading(self, heading: str) -> bool:
        return bool(self.STRUCTURED_HEADING_PATTERN.match(heading))

    @staticmethod
    def _looks_like_source_or_footer_heading(heading: str) -> bool:
        compact = heading.lower()
        return (
            "\u6570\u636e\u6765\u6e90" in compact
            or "\u8d44\u6599\u6765\u6e90" in compact
            or "source:" in compact
            or "\u7279\u522b\u58f0\u660e" in compact
            or "important notice" in compact
        )

    @staticmethod
    def _looks_like_page_label(heading: str) -> bool:
        return bool(re.fullmatch(r"\d{1,4}", heading))

    @staticmethod
    def _looks_like_date_or_period_heading(heading: str) -> bool:
        normalized = re.sub(r"\s+", "", heading.lower())
        return bool(
            re.fullmatch(
                r"(20\d{2}(?:[-/\u5e74]\d{1,2}(?:[-/\u6708]\d{1,2}\u65e5?)?)?|"
                r"\d{4}[qehm]\d{1,2}|"
                r"\d{4}[\u5e74]?\d{0,2}[\u6708]?\d{0,2}[\u65e5]?)",
                normalized,
            )
        )
