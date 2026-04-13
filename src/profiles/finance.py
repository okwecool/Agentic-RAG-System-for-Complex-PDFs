"""Finance profile placeholder."""

from src.domain.models.document import Document
from src.profiles.base import BaseProfile


class FinanceProfile(BaseProfile):
    name = "finance"

    def detect(self, document: Document) -> bool:
        text = " ".join(
            block.text.lower()
            for page in document.pages
            for block in page.blocks
            if block.text
        )
        return "ticker" in text or "analyst" in text

