"""Section path construction helpers."""

import re

from src.domain.models.document import Document


class SectionBuilder:
    def apply(self, document: Document) -> Document:
        current_section = ["Document"]
        for page in document.pages:
            for block in page.blocks:
                if block.type == "heading" and block.text.strip():
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
