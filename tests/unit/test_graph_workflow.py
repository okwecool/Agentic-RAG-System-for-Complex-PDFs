from __future__ import annotations

import unittest

from src.graph.nodes.retrieval_strategist import RetrievalStrategistNode
from src.graph.router import Router
from src.graph.workflow import QueryWorkflow


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = Router()

    def test_router_routes_to_planner_when_plan_missing(self) -> None:
        decision = self.router.decide({"user_query": "Sora 2 有什么升级？"})

        self.assertEqual(decision["next_node"], "query_planner")
        self.assertEqual(decision["reason"], "missing_plan")
        self.assertTrue(decision["should_continue"])

    def test_router_routes_to_retrieval_when_candidates_missing(self) -> None:
        decision = self.router.decide(
            {
                "user_query": "Sora 2 有什么升级？",
                "current_intent": "qa",
                "retrieval_plan": {"mode": "default"},
            }
        )

        self.assertEqual(decision["next_node"], "retrieval_strategist")
        self.assertEqual(decision["reason"], "missing_candidates")

    def test_router_routes_to_synthesizer_when_evidence_ready(self) -> None:
        decision = self.router.decide(
            {
                "current_intent": "qa",
                "retrieval_plan": {"mode": "default"},
                "retrieved_candidates": [{"chunk_id": "c1"}],
                "selected_evidence": [{"chunk_id": "c1"}],
                "selected_evidence_types": ["narrative_evidence"],
                "retry_count": 1,
                "max_retry_count": 2,
            }
        )

        self.assertEqual(decision["next_node"], "synthesizer")
        self.assertEqual(decision["reason"], "ready_to_synthesize")

    def test_router_routes_to_audit_when_answer_exists(self) -> None:
        decision = self.router.decide(
            {
                "current_intent": "qa",
                "retrieval_plan": {"mode": "default"},
                "retrieved_candidates": [{"chunk_id": "c1"}],
                "selected_evidence": [{"chunk_id": "c1"}],
                "selected_evidence_types": ["narrative_evidence"],
                "draft_answer": "测试答案",
            }
        )

        self.assertEqual(decision["next_node"], "citation_auditor")
        self.assertEqual(decision["reason"], "missing_citation_audit")

    def test_router_finishes_when_citation_map_exists(self) -> None:
        decision = self.router.decide(
            {
                "current_intent": "qa",
                "retrieval_plan": {"mode": "default"},
                "retrieved_candidates": [{"chunk_id": "c1"}],
                "selected_evidence": [{"chunk_id": "c1"}],
                "selected_evidence_types": ["narrative_evidence"],
                "draft_answer": "测试答案",
                "citation_map": [{"claim": "x"}],
            }
        )

        self.assertEqual(decision["next_node"], "finish")
        self.assertFalse(decision["should_continue"])


class QueryWorkflowTests(unittest.TestCase):
    def test_workflow_runs_until_completed(self) -> None:
        workflow = QueryWorkflow()

        state = workflow.run({"user_query": "Sora 2 有什么升级？"})

        self.assertEqual(state["workflow_status"], "completed")
        self.assertEqual(state["route_decision"]["next_node"], "finish")
        self.assertIn("retrieval_plan", state)
        self.assertIn("retrieved_candidates", state)
        self.assertIn("draft_answer", state)
        self.assertIn("citation_map", state)


class _FakeSearchService:
    def search_chunks(self, query: str, top_k: int = 10) -> list[dict]:
        from src.domain.models.document import Chunk

        return [
            {
                "chunk": Chunk(
                    chunk_id="doc_test_p3_c1",
                    doc_id="doc_test",
                    text="Sora 2 实现了音视频同步。",
                    page_no=3,
                    chunk_type="paragraph",
                    metadata={"document_source_type": "research_report"},
                ),
                "score": 0.92,
                "sources": ["bm25", "vector"],
            },
            {
                "chunk": Chunk(
                    chunk_id="doc_test_p4_c2",
                    doc_id="doc_test",
                    text="图表 5：Sora 2 真实度提升。",
                    page_no=4,
                    chunk_type="heading",
                    metadata={"document_source_type": "research_report"},
                ),
                "score": 0.77,
                "sources": ["vector"],
            },
        ][:top_k]

    def search_tables(self, query: str, top_k: int = 10) -> list[dict]:
        from src.domain.models.document import Chunk

        return [
            {
                "chunk": Chunk(
                    chunk_id="doc_test_p5_c3",
                    doc_id="doc_test",
                    text="表头: 指标 | 值",
                    page_no=5,
                    chunk_type="table",
                    metadata={"document_source_type": "research_report"},
                ),
                "score": 0.88,
                "sources": ["vector"],
            }
        ][:top_k]


class RetrievalStrategistNodeTests(unittest.TestCase):
    def test_retrieval_strategist_uses_search_service_for_chunks(self) -> None:
        node = RetrievalStrategistNode(search_service=_FakeSearchService(), default_top_k=2)

        state = node.run(
            {
                "user_query": "Sora 2 有什么升级？",
                "normalized_query": "Sora 2 有什么升级？",
                "retrieval_plan": {"top_k": 2, "tables_only": False},
            }
        )

        self.assertEqual(len(state["retrieved_candidates"]), 2)
        self.assertEqual(state["candidate_evidence_types"], ["narrative_evidence", "caption_evidence"])
        self.assertEqual(state["document_source_types"], ["research_report", "research_report"])

    def test_retrieval_strategist_uses_search_service_for_tables(self) -> None:
        node = RetrievalStrategistNode(search_service=_FakeSearchService(), default_top_k=2)

        state = node.run(
            {
                "user_query": "比亚迪 销量",
                "normalized_query": "比亚迪 销量",
                "retrieval_plan": {"top_k": 1, "tables_only": True},
            }
        )

        self.assertEqual(len(state["retrieved_candidates"]), 1)
        self.assertEqual(state["candidate_evidence_types"], ["table_evidence"])


if __name__ == "__main__":
    unittest.main()
