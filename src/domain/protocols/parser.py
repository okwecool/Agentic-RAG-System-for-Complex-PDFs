"""Parser protocol."""

from typing import Protocol

from src.domain.models.document import Document


class Parser(Protocol):
    def parse(self, file_path: str) -> Document:
        """Parse a PDF into a structured document."""

