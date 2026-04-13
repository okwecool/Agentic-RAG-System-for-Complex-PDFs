"""Index build orchestration."""

from __future__ import annotations

import json
from pathlib import Path

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

    def build_from_chunk_files(self, chunks_dir: Path) -> list[Chunk]:
        chunks = self.load_chunks_from_chunk_files(chunks_dir)
        self.build(chunks)
        return chunks

    @staticmethod
    def load_chunks_from_chunk_files(chunks_dir: Path) -> list[Chunk]:
        chunks: list[Chunk] = []
        for chunk_file in sorted(chunks_dir.glob("*.json")):
            payload = json.loads(chunk_file.read_text(encoding="utf-8"))
            doc_id = payload["doc_id"]
            for item in payload.get("chunks", []):
                chunks.append(
                    Chunk(
                        chunk_id=item["chunk_id"],
                        doc_id=doc_id,
                        text=item["text"],
                        page_no=int(item["page_no"]),
                        chunk_type=item.get("chunk_type", "paragraph"),
                        section_path=item.get("section_path", []),
                        metadata=item.get("metadata", {}),
                    )
                )
        return chunks
