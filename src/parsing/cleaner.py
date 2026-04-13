"""Block cleaning helpers."""

from src.domain.models.document import Document


class DocumentCleaner:
    def clean(self, document: Document) -> Document:
        for page in document.pages:
            page.blocks = [block for block in page.blocks if block.text.strip()]
        return document

