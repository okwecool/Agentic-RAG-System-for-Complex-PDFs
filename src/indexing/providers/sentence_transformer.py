"""SentenceTransformer embedding provider."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.indexing.providers.base import BaseEmbeddingProvider


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    backend = "sentence_transformer"

    def __init__(self, model_name_or_path: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name_or_path = model_name_or_path
        self._model = SentenceTransformer(model_name_or_path, device="cpu")
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        matrix = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=16,
            show_progress_bar=True,
        )
        return np.asarray(matrix, dtype="float32").tolist()

    def embed_query(self, query: str) -> list[float]:
        vector = self._model.encode(
            [query],
            normalize_embeddings=True,
            batch_size=1,
            show_progress_bar=False,
        )[0]
        return np.asarray(vector, dtype="float32").tolist()

    def save_state(self, output_dir: Path) -> None:
        del output_dir
