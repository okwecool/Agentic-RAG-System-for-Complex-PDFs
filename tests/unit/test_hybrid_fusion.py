import unittest

from src.domain.models.document import Chunk
from src.retrieval.hybrid_fusion import HybridFusion


class HybridFusionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunk_a = Chunk(
            chunk_id="a",
            doc_id="doc1",
            text="alpha",
            page_no=1,
            chunk_type="paragraph",
            section_path=["Document"],
            metadata={"page_no": 1},
        )
        self.chunk_b = Chunk(
            chunk_id="b",
            doc_id="doc1",
            text="beta",
            page_no=1,
            chunk_type="paragraph",
            section_path=["Document"],
            metadata={"page_no": 1},
        )
        self.bm25_results = [
            {"chunk": self.chunk_a, "score": 10.0, "source": "bm25"},
            {"chunk": self.chunk_b, "score": 9.0, "source": "bm25"},
        ]
        self.vector_results = [
            {"chunk": self.chunk_b, "score": 0.9, "source": "vector"},
            {"chunk": self.chunk_a, "score": 0.8, "source": "vector"},
        ]

    def test_rrf_fusion_returns_combined_results(self) -> None:
        fusion = HybridFusion(mode="rrf", rrf_k=60)

        results = fusion.fuse(self.bm25_results, self.vector_results, top_k=2)

        self.assertEqual(2, len(results))
        self.assertCountEqual(["a", "b"], [item["chunk"].chunk_id for item in results])

    def test_weighted_rank_fusion_prefers_bm25_when_weight_is_higher(self) -> None:
        fusion = HybridFusion(
            mode="weighted_rank",
            bm25_weight=2.0,
            vector_weight=0.5,
        )

        results = fusion.fuse(self.bm25_results, self.vector_results, top_k=2)

        self.assertEqual("a", results[0]["chunk"].chunk_id)

    def test_weighted_rank_fusion_prefers_vector_when_weight_is_higher(self) -> None:
        fusion = HybridFusion(
            mode="weighted_rank",
            bm25_weight=0.5,
            vector_weight=2.0,
        )

        results = fusion.fuse(self.bm25_results, self.vector_results, top_k=2)

        self.assertEqual("b", results[0]["chunk"].chunk_id)
