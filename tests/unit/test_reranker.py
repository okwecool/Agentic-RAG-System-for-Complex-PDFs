import unittest

from src.domain.models.document import Chunk
from src.retrieval.rerankers.noop import NoOpReranker


class RerankerTests(unittest.TestCase):
    def test_noop_reranker_preserves_order(self) -> None:
        reranker = NoOpReranker()
        candidates = [
            {
                "chunk": Chunk(
                    chunk_id="c1",
                    doc_id="doc1",
                    text="alpha",
                    page_no=1,
                    chunk_type="paragraph",
                    section_path=["Document"],
                    metadata={"page_no": 1},
                ),
                "score": 1.0,
            },
            {
                "chunk": Chunk(
                    chunk_id="c2",
                    doc_id="doc1",
                    text="beta",
                    page_no=1,
                    chunk_type="paragraph",
                    section_path=["Document"],
                    metadata={"page_no": 1},
                ),
                "score": 0.9,
            },
        ]

        results = reranker.rerank("test query", candidates)

        self.assertEqual(["c1", "c2"], [item["chunk"].chunk_id for item in results])
