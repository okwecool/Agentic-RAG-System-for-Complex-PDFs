"""Local embedding service used for baseline retrieval."""

from __future__ import annotations

from hashlib import sha1

from src.domain.models.document import Chunk
from src.indexing.text_utils import l2_normalize, tokenize_for_retrieval


class EmbeddingService:
    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions

    def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        return [self._embed_text(chunk.text) for chunk in chunks]

    def embed_query(self, query: str) -> list[float]:
        return self._embed_text(query)

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = tokenize_for_retrieval(text)
        if not tokens:
            return vector

        for token in tokens:
            index = self._token_index(token)
            vector[index] += 1.0

        return l2_normalize(vector)

    def _token_index(self, token: str) -> int:
        digest = sha1(token.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], byteorder="big", signed=False)
        return value % self.dimensions
