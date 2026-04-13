"""Search orchestration service."""

from src.indexing.bm25_index import Bm25Index
from src.indexing.embeddings import EmbeddingService
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

    def search_chunks(self, query: str, top_k: int = 10) -> list[dict]:
        query_vector = self.embedding_service.embed_query(query)
        bm25_results = self.bm25_index.search(query, top_k=top_k)
        vector_results = self.vector_index.search(query_vector, top_k=top_k)
        fused = self.fusion.fuse(bm25_results, vector_results, top_k=top_k)
        return self.reranker.rerank(query, fused)

