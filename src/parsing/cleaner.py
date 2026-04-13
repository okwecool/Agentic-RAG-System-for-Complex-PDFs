"""Block cleaning helpers."""

from collections import Counter
import re

from src.domain.models.document import Document


class DocumentCleaner:
    def clean(self, document: Document) -> Document:
        repeated_noise = self._find_repeated_noise(document)
        for page in document.pages:
            cleaned_blocks = []
            for block in page.blocks:
                cleaned_text = self._normalize_text(block.text)
                if not cleaned_text or self._is_noise(cleaned_text, repeated_noise):
                    continue
                block.text = cleaned_text
                cleaned_blocks.append(block)
            page.blocks = cleaned_blocks
        return document

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _is_noise(text: str, repeated_noise: set[str]) -> bool:
        compact = text.strip()
        if len(compact) <= 1:
            return True
        if re.fullmatch(r"\d+", compact):
            return True
        if re.fullmatch(r"page\s+\d+(\s+of\s+\d+)?", compact.lower()):
            return True
        if compact in repeated_noise:
            return True
        return False

    @staticmethod
    def _find_repeated_noise(document: Document) -> set[str]:
        if len(document.pages) < 2:
            return set()
        counts: Counter[str] = Counter()
        for page in document.pages:
            unique_texts = {
                re.sub(r"\s+", " ", block.text).strip()
                for block in page.blocks
                if block.text and len(block.text.strip()) <= 30
            }
            counts.update(unique_texts)
        return {text for text, count in counts.items() if count >= 2}
