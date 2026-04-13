"""Section path construction helpers."""

from src.domain.models.document import Document


class SectionBuilder:
    def apply(self, document: Document) -> Document:
        current_section = ["Document"]
        for page in document.pages:
            for block in page.blocks:
                if block.type == "heading" and block.text.strip():
                    current_section = [block.text.strip()]
                if not block.section_path:
                    block.section_path = current_section.copy()
        return document

