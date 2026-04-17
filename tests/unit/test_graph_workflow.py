from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
