"""Index build orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

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

    def build_and_persist(self, chunks_dir: Path, output_dir: Path) -> dict[str, int | str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        chunks = self.load_chunks_from_chunk_files(chunks_dir)
        vectors = self.embedding_service.embed_chunks(chunks)
        self.vector_index.add(chunks, vectors)
        self.bm25_index.add(chunks)

        self._write_chunks_metadata(chunks, output_dir / "chunks.json")
        np.save(output_dir / "vectors.npy", np.asarray(vectors, dtype="float32"))
        self.embedding_service.save_state(output_dir)

        manifest = {
            "chunk_count": len(chunks),
            "embedding_backend": getattr(self.embedding_service, "backend", "unknown"),
            "embedding_model_path": getattr(self.embedding_service, "model_name_or_path", None),
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest

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

    @staticmethod
    def load_chunks_metadata(metadata_path: Path) -> list[Chunk]:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        chunks: list[Chunk] = []
        for item in payload:
            chunks.append(
                Chunk(
                    chunk_id=item["chunk_id"],
                    doc_id=item["doc_id"],
                    text=item["text"],
                    page_no=int(item["page_no"]),
                    chunk_type=item.get("chunk_type", "paragraph"),
                    section_path=item.get("section_path", []),
                    metadata=item.get("metadata", {}),
                )
            )
        return chunks

    @staticmethod
    def _write_chunks_metadata(chunks: list[Chunk], output_path: Path) -> None:
        payload = [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "text": chunk.text,
                "page_no": chunk.page_no,
                "chunk_type": chunk.chunk_type,
                "section_path": chunk.section_path,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
