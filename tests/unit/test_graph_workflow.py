from __future__ import annotations

import unittest

from src.generation.answer_generator import AnswerGenerator
from src.generation.citation_auditor import CitationAuditor
from src.generation.prompts.qwen import QwenPromptTemplate
from src.graph import route_rules
from src.graph.nodes.citation_auditor import CitationAuditorNode
from src.graph.nodes.conversation_resolver import ConversationResolverNode
from src.graph.nodes.query_planner import QueryPlannerNode
from src.graph.nodes.retrieval_strategist import RetrievalStrategistNode
from src.graph.nodes.synthesizer import SynthesizerNode
from src.graph.router import Router
from src.graph.workflow import QueryWorkflow


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = Router()

    def test_router_routes_to_conversation_resolver_when_query_not_resolved(self) -> None:
        decision = self.router.decide({"user_query": "Sora 2 有什么升级？"})

        self.assertEqual(decision["next_node"], "conversation_resolver")
        self.assertEqual(decision["reason"], "missing_conversation_resolution")
        self.assertTrue(decision["should_continue"])

    def test_router_routes_to_planner_when_plan_missing(self) -> None:
        decision = self.router.decide(
            {
                "user_query": "Sora 2 有什么升级？",
                "resolved_user_query": "Sora 2 有什么升级？",
            }
        )

        self.assertEqual(decision["next_node"], "query_planner")
        self.assertEqual(decision["reason"], "missing_plan")
        self.assertTrue(decision["should_continue"])

    def test_router_does_not_treat_request_options_as_plan(self) -> None:
        decision = self.router.decide(
            {
                "user_query": "关于比亚迪有哪些商业信息？",
                "resolved_user_query": "关于比亚迪有哪些商业信息？",
                "request_options": {"top_k": 6, "tables_only": False},
            }
        )

        self.assertEqual(decision["next_node"], "query_planner")
        self.assertEqual(decision["reason"], "missing_plan")

    def test_router_routes_to_retrieval_when_candidates_missing(self) -> None:
        decision = self.router.decide(
            {
                "user_query": "Sora 2 有什么升级？",
                "resolved_user_query": "Sora 2 有什么升级？",
                "current_intent": "qa",
                "retrieval_plan": {"mode": "hybrid", "intent": "qa", "complexity": "low"},
            }
        )

        self.assertEqual(decision["next_node"], "retrieval_strategist")
        self.assertEqual(decision["reason"], "missing_candidates")

    def test_router_routes_to_synthesizer_when_evidence_ready(self) -> None:
        decision = self.router.decide(
            {
                "resolved_user_query": "Sora 2 有什么升级？",
                "current_intent": "qa",
                "retrieval_plan": {"mode": "hybrid", "intent": "qa", "complexity": "low"},
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
                "resolved_user_query": "测试问题",
                "current_intent": "qa",
                "retrieval_plan": {"mode": "hybrid", "intent": "qa", "complexity": "low"},
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
                "resolved_user_query": "测试问题",
                "current_intent": "qa",
                "retrieval_plan": {"mode": "hybrid", "intent": "qa", "complexity": "low"},
                "retrieved_candidates": [{"chunk_id": "c1"}],
                "selected_evidence": [{"chunk_id": "c1"}],
                "selected_evidence_types": ["narrative_evidence"],
                "draft_answer": "测试答案",
                "citation_map": [{"claim": "x"}],
            }
        )

        self.assertEqual(decision["next_node"], "finish")
        self.assertFalse(decision["should_continue"])


class RouteRulesTests(unittest.TestCase):
    def test_has_plan_requires_real_planning_fields(self) -> None:
        self.assertFalse(route_rules.has_plan({"retrieval_plan": {"top_k": 6}}))
        self.assertTrue(
            route_rules.has_plan(
                {"retrieval_plan": {"mode": "hybrid", "intent": "qa", "complexity": "low"}}
            )
        )


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
        self.assertIn("route_trace", state)
        self.assertGreaterEqual(len(state["route_trace"]), 1)
        self.assertEqual("conversation_resolver", state["route_trace"][0]["next_node"])


class ConversationResolverNodeTests(unittest.TestCase):
    def test_conversation_resolver_uses_previous_entity_for_follow_up_question(self) -> None:
        node = ConversationResolverNode()

        state = node.run(
            {
                "user_query": "那它今年呢？",
                "messages": [
                    {"role": "user", "content": "英伟达近期发展势头如何？"},
                    {"role": "assistant", "content": "英伟达近期发展势头强劲。"},
                ],
                "current_entities": {"last_entity": "英伟达"},
            }
        )

        self.assertEqual("英伟达今年呢？", state["resolved_user_query"])
        self.assertEqual("query_planner", state["next_action"])

    def test_conversation_resolver_handles_company_follow_up_reference(self) -> None:
        node = ConversationResolverNode()

        state = node.run(
            {
                "user_query": "这家公司最近怎么样？",
                "messages": [
                    {"role": "user", "content": "请总结一下比亚迪的商业信息"},
                    {"role": "assistant", "content": "比亚迪近期在海外市场扩张明显。"},
                ],
                "current_entities": {"last_entity": "比亚迪"},
            }
        )

        self.assertEqual("比亚迪最近怎么样？", state["resolved_user_query"])
        self.assertEqual("query_planner", state["next_action"])


class QueryPlannerNodeTests(unittest.TestCase):
    def test_query_planner_builds_normalized_query_and_plan(self) -> None:
        node = QueryPlannerNode()

        state = node.run({"user_query": "  Sora 2   有什么升级？  "})

        self.assertEqual(state["normalized_query"], "Sora 2 有什么升级?")
        self.assertEqual(state["current_intent"], "qa")
        self.assertEqual(state["retrieval_plan"]["mode"], "hybrid")
        self.assertEqual(state["next_action"], "retrieval_strategist")

    def test_query_planner_marks_structured_query_preferences(self) -> None:
        node = QueryPlannerNode()

        state = node.run({"user_query": "比亚迪 图表 2025 年销量对比"})

        self.assertEqual(state["current_intent"], "compare")
        self.assertTrue(state["retrieval_plan"]["prefers_structured_blocks"])
        self.assertTrue(state["retrieval_plan"]["tables_only"])
        self.assertEqual(state["current_time_range"]["years"], ["2025"])
        self.assertIn("structured_preferred", state["current_sub_intents"])

    def test_query_planner_applies_request_options_over_defaults(self) -> None:
        node = QueryPlannerNode()

        state = node.run(
            {
                "user_query": "关于比亚迪有哪些商业信息？",
                "request_options": {"top_k": 6, "tables_only": False},
            }
        )

        self.assertEqual(6, state["retrieval_plan"]["top_k"])
        self.assertFalse(state["retrieval_plan"]["tables_only"])


class _FakeSearchService:
    embedding_backend = "fake-embedding"

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


class _FakeLlmProvider:
    backend = "fake"
    model_name = "fake-model"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "根据证据，Sora 2 实现了原生音视频同步。"


class RetrievalStrategistNodeTests(unittest.TestCase):
    def test_retrieval_strategist_strict_mode_fails_without_service(self) -> None:
        node = RetrievalStrategistNode(strict=True)

        with self.assertRaises(RuntimeError):
            node.run({"user_query": "Sora 2 有什么升级？"})

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
        self.assertEqual(
            state["candidate_evidence_types"],
            ["narrative_evidence", "caption_evidence"],
        )
        self.assertEqual(
            state["document_source_types"],
            ["research_report", "research_report"],
        )

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


class GenerationNodeTests(unittest.TestCase):
    def test_synthesizer_node_strict_mode_fails_without_generator(self) -> None:
        node = SynthesizerNode(strict=True)

        with self.assertRaises(RuntimeError):
            node.run({"user_query": "Sora 2 有什么升级？"})

    def test_synthesizer_node_uses_answer_generator(self) -> None:
        node = SynthesizerNode(
            answer_generator=AnswerGenerator(_FakeLlmProvider(), QwenPromptTemplate()),
            default_top_k=2,
        )
        state = node.run(
            {
                "user_query": "Sora 2 有什么升级？",
                "normalized_query": "Sora 2 有什么升级？",
                "retrieval_plan": {"top_k": 2},
                "selected_evidence": _FakeSearchService().search_chunks("Sora 2", top_k=1),
            }
        )

        self.assertIn("原生音视频同步", state["draft_answer"])
        self.assertEqual(state["confidence"], "medium")
        self.assertEqual(state["next_action"], "citation_auditor")
        self.assertEqual(len(state["claims"]), 1)

    def test_citation_auditor_node_uses_auditor(self) -> None:
        node = CitationAuditorNode(citation_auditor=CitationAuditor())
        evidence = _FakeSearchService().search_chunks("Sora 2", top_k=1)
        state = node.run(
            {
                "claims": [
                    {
                        "claim": "根据证据，Sora 2 实现了原生音视频同步。",
                        "supporting_chunk_ids": ["doc_test_p3_c1"],
                    }
                ],
                "selected_evidence": evidence,
                "confidence": "medium",
            }
        )

        self.assertEqual(len(state["citation_map"]), 1)
        self.assertEqual(state["confidence"], "medium")

    def test_citation_auditor_node_strict_mode_fails_without_auditor(self) -> None:
        node = CitationAuditorNode(strict=True)

        with self.assertRaises(RuntimeError):
            node.run({"claims": [], "selected_evidence": []})


if __name__ == "__main__":
    unittest.main()
