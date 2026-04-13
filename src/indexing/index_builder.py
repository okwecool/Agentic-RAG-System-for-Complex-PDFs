"""Index build orchestration."""

from src.domain.models.document import Chunk
from src.indexing.bm25_index import Bm25Index
from src.indexing.embeddings import EmbeddingService
from src.indexing.vector_index import VectorIndex


class IndexBuilder:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_index: VectorIndex,
        bm25_index: Bm25Index,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_index = vector_index
        self.bm25_index = bm25_index

    def build(self, chunks: list[Chunk]) -> None:
        vectors = self.embedding_service.embed_chunks(chunks)
        self.vector_index.add(chunks, vectors)
        self.bm25_index.add(chunks)

