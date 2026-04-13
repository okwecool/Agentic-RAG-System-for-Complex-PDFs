"""Chunker protocol."""

from typing import Protocol

from src.domain.models.document import Chunk, Document


class Chunker(Protocol):
    def chunk(self, document: Document) -> list[Chunk]:
        """Split a document into retrieval chunks."""

