"""Search orchestration service."""

from __future__ import annotations

from pathlib import Path

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
    def from_chunk_artifacts(chunks_dir: Path) -> "SearchService":
        embedding_service = EmbeddingService()
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
    def _filter_results(results: list[dict], chunk_types: set[str] | None) -> list[dict]:
        if not chunk_types:
            return results
        return [item for item in results if item["chunk"].chunk_type in chunk_types]
