"""Search orchestration service."""

from __future__ import annotations

import json
from pathlib import Path
import pickle

import numpy as np

from src.indexing.bm25_index import Bm25Index
from src.indexing.embeddings import EmbeddingService
from src.indexing.index_builder import IndexBuilder
from src.indexing.vector_index import VectorIndex
from src.retrieval.hybrid_fusion import HybridFusion
from src.retrieval.rerank import NoOpReranker


class SearchService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_index: VectorIndex,
        bm25_index: Bm25Index,
        fusion: HybridFusion,
        reranker: NoOpReranker,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_index = vector_index
        self.bm25_index = bm25_index
        self.fusion = fusion
        self.reranker = reranker

    @property
    def embedding_backend(self) -> str:
        return getattr(self.embedding_service, "backend", "unknown")

    def search_chunks(
        self,
        query: str,
        top_k: int = 10,
        chunk_types: set[str] | None = None,
    ) -> list[dict]:
        query_vector = self.embedding_service.embed_query(query)
        bm25_results = self.bm25_index.search(query, top_k=max(top_k * 2, top_k))
        vector_results = self.vector_index.search(query_vector, top_k=max(top_k * 2, top_k))
        fused = self.fusion.fuse(bm25_results, vector_results, top_k=max(top_k * 3, top_k))
        filtered = self._filter_results(fused, chunk_types=chunk_types)
        reranked = self.reranker.rerank(query, filtered)
        return reranked[:top_k]

    def search_tables(self, query: str, top_k: int = 10) -> list[dict]:
        return self.search_chunks(query, top_k=top_k, chunk_types={"table"})

    @staticmethod
    def from_chunk_artifacts(
        chunks_dir: Path,
        embedding_model_path: str | None = None,
    ) -> "SearchService":
        embedding_service = EmbeddingService(model_name_or_path=embedding_model_path)
        vector_index = VectorIndex()
        bm25_index = Bm25Index()
        builder = IndexBuilder(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
        )
        builder.build_from_chunk_files(chunks_dir)
        return SearchService(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
            fusion=HybridFusion(),
            reranker=NoOpReranker(),
        )

    @staticmethod
    def from_persisted_index(
        index_dir: Path,
        embedding_model_path: str | None = None,
    ) -> "SearchService":
        manifest_path = index_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing manifest: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        resolved_model_path = embedding_model_path or manifest.get("embedding_model_path")
        embedding_service = EmbeddingService(model_name_or_path=resolved_model_path)
        if manifest.get("embedding_backend") == "tfidf":
            vectorizer_path = index_dir / "vectorizer.pkl"
            if vectorizer_path.exists():
                with vectorizer_path.open("rb") as handle:
                    embedding_service._vectorizer = pickle.load(handle)
                embedding_service._fitted = True
        vector_index = VectorIndex()
        bm25_index = Bm25Index()

        chunks = IndexBuilder.load_chunks_metadata(index_dir / "chunks.json")
        vectors = np.load(index_dir / "vectors.npy").astype("float32").tolist()
        vector_index.add(chunks, vectors)
        bm25_index.add(chunks)

        return SearchService(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
            fusion=HybridFusion(),
            reranker=NoOpReranker(),
        )

    @staticmethod
    def _filter_results(results: list[dict], chunk_types: set[str] | None) -> list[dict]:
        if not chunk_types:
            return results
        return [item for item in results if item["chunk"].chunk_type in chunk_types]
