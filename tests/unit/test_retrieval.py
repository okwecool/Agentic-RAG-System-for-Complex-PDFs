import json
import unittest
from pathlib import Path

from src.domain.models.document import Chunk
from src.indexing.bm25_index import Bm25Index
from src.indexing.embeddings import EmbeddingService
from src.indexing.index_builder import IndexBuilder
from src.indexing.vector_index import VectorIndex
from src.retrieval.hybrid_fusion import HybridFusion
from src.retrieval.rerank import NoOpReranker
from src.retrieval.search_service import SearchService
from src.config.settings import get_settings


class RetrievalFrameworkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = [
            Chunk(
                chunk_id="c1",
                doc_id="doc1",
                text="OpenAI 推出 Sora 2 视频生成模型",
                page_no=1,
                chunk_type="paragraph",
                section_path=["Document"],
                metadata={"page_no": 1},
            ),
            Chunk(
                chunk_id="c2",
                doc_id="doc1",
                text="汽车销量表 比亚迪 销量 市占率",
                page_no=2,
                chunk_type="table",
                section_path=["Document"],
                metadata={"page_no": 2},
            ),
            Chunk(
                chunk_id="c3",
                doc_id="doc2",
                text="半导体设备需求回暖",
                page_no=1,
                chunk_type="paragraph",
                section_path=["Document"],
                metadata={"page_no": 1},
            ),
        ]

    def _build_service(self) -> SearchService:
        embedding_service = EmbeddingService(dimensions=64)
        vector_index = VectorIndex()
        bm25_index = Bm25Index()
        builder = IndexBuilder(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
        )
        builder.build(self.chunks)
        return SearchService(
            embedding_service=embedding_service,
            vector_index=vector_index,
            bm25_index=bm25_index,
            fusion=HybridFusion(),
            reranker=NoOpReranker(),
        )

    def test_bm25_returns_relevant_chunk(self) -> None:
        index = Bm25Index()
        index.add(self.chunks)

        results = index.search("Sora 视频生成", top_k=2)

        self.assertEqual(results[0]["chunk"].chunk_id, "c1")
        self.assertGreater(results[0]["score"], 0.0)

    def test_vector_search_returns_semantically_similar_chunk(self) -> None:
        embedding_service = EmbeddingService(dimensions=64)
        index = VectorIndex()
        index.add(self.chunks, embedding_service.embed_chunks(self.chunks))

        results = index.search(embedding_service.embed_query("比亚迪销量"), top_k=2)

        self.assertEqual(results[0]["chunk"].chunk_id, "c2")

    def test_search_service_supports_hybrid_and_table_filter(self) -> None:
        service = self._build_service()

        hybrid_results = service.search_chunks("OpenAI Sora", top_k=2)
        table_results = service.search_tables("比亚迪 销量", top_k=2)

        self.assertEqual(hybrid_results[0]["chunk"].chunk_id, "c1")
        self.assertEqual(table_results[0]["chunk"].chunk_id, "c2")
        self.assertTrue(all(item["chunk"].chunk_type == "table" for item in table_results))

    def test_index_builder_loads_chunk_artifacts(self) -> None:
        settings = get_settings()
        chunks_dir = settings.artifacts_dir / "test_chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        try:
            payload = {
                "doc_id": "doc_demo",
                "title": "demo",
                "source_file": "demo.pdf",
                "chunk_count": 2,
                "chunks": [
                    {
                        "chunk_id": "doc_demo_p1_c1",
                        "page_no": 1,
                        "chunk_type": "paragraph",
                        "section_path": ["Document"],
                        "metadata": {"page_no": 1},
                        "text": "OpenAI 发布新模型",
                    },
                    {
                        "chunk_id": "doc_demo_p1_c2",
                        "page_no": 1,
                        "chunk_type": "table",
                        "section_path": ["Document"],
                        "metadata": {"page_no": 1},
                        "text": "比亚迪 销量 份额",
                    },
                ],
            }
            (chunks_dir / "doc_demo.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            loaded_chunks = IndexBuilder.load_chunks_from_chunk_files(chunks_dir)
            service = SearchService.from_chunk_artifacts(chunks_dir)
        finally:
            for file_path in chunks_dir.glob("*.json"):
                file_path.unlink()
            chunks_dir.rmdir()

        self.assertEqual(len(loaded_chunks), 2)
        results = service.search_chunks("OpenAI 模型", top_k=1)
        self.assertEqual(results[0]["chunk"].chunk_id, "doc_demo_p1_c1")

    def test_search_service_loads_persisted_index(self) -> None:
        settings = get_settings()
        chunks_dir = settings.artifacts_dir / "test_chunks_persist"
        index_dir = settings.indexes_dir / "test_retrieval_cache"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        index_dir.mkdir(parents=True, exist_ok=True)
        try:
            payload = {
                "doc_id": "doc_demo",
                "title": "demo",
                "source_file": "demo.pdf",
                "chunk_count": 2,
                "chunks": [
                    {
                        "chunk_id": "doc_demo_p1_c1",
                        "page_no": 1,
                        "chunk_type": "paragraph",
                        "section_path": ["Document"],
                        "metadata": {"page_no": 1},
                        "text": "OpenAI 发布新模型",
                    },
                    {
                        "chunk_id": "doc_demo_p1_c2",
                        "page_no": 1,
                        "chunk_type": "table",
                        "section_path": ["Document"],
                        "metadata": {"page_no": 1},
                        "text": "比亚迪 销量 份额",
                    },
                ],
            }
            (chunks_dir / "doc_demo.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            builder = IndexBuilder(
                embedding_service=EmbeddingService(dimensions=64),
                vector_index=VectorIndex(),
                bm25_index=Bm25Index(),
            )
            builder.build_and_persist(chunks_dir=chunks_dir, output_dir=index_dir)
            service = SearchService.from_persisted_index(index_dir=index_dir)
        finally:
            for file_path in chunks_dir.glob("*.json"):
                file_path.unlink()
            chunks_dir.rmdir()
            for file_path in index_dir.glob("*"):
                file_path.unlink()
            index_dir.rmdir()

        results = service.search_tables("比亚迪 销量", top_k=1)
        self.assertEqual(results[0]["chunk"].chunk_id, "doc_demo_p1_c2")


if __name__ == "__main__":
    unittest.main()
