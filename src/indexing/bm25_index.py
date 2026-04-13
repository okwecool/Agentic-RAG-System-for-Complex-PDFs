"""In-memory BM25 index."""

from __future__ import annotations

from collections import Counter
import math

from src.domain.models.document import Chunk
from src.indexing.text_utils import tokenize_for_retrieval


class Bm25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._chunks: list[Chunk] = []
        self._term_frequencies: list[Counter[str]] = []
        self._doc_frequencies: Counter[str] = Counter()
        self._doc_lengths: list[int] = []

    def add(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            tokens = tokenize_for_retrieval(chunk.text)
            term_frequency = Counter(tokens)
            self._chunks.append(chunk)
            self._term_frequencies.append(term_frequency)
            self._doc_lengths.append(len(tokens))
            for token in term_frequency:
                self._doc_frequencies[token] += 1

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        query_tokens = tokenize_for_retrieval(query)
        if not query_tokens or not self._chunks:
            return []

        average_doc_length = sum(self._doc_lengths) / max(1, len(self._doc_lengths))
        scored: list[dict] = []
        for index, chunk in enumerate(self._chunks):
            score = self._score_chunk(
                index=index,
                query_tokens=query_tokens,
                average_doc_length=average_doc_length,
            )
            if score <= 0.0:
                continue
            scored.append({"chunk": chunk, "score": score, "source": "bm25"})

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def _score_chunk(
        self,
        index: int,
        query_tokens: list[str],
        average_doc_length: float,
    ) -> float:
        score = 0.0
        term_frequency = self._term_frequencies[index]
        doc_length = self._doc_lengths[index]
        document_count = len(self._chunks)

        for token in query_tokens:
            tf = term_frequency.get(token, 0)
            if tf == 0:
                continue
            df = self._doc_frequencies.get(token, 0)
            if df == 0:
                continue
            idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * doc_length / max(average_doc_length, 1e-6)
            )
            score += idf * (numerator / max(denominator, 1e-6))

        return score
