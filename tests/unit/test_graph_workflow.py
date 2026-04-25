from __future__ import annotations

import unittest

from src.generation.answer_generator import AnswerGenerator
from src.generation.citation_auditor import CitationAuditor
from src.generation.prompts.qwen import QwenPromptTemplate
from src.entity_resolution.rule_resolver import RuleEntityResolver
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
        self.assertTrue(state["conversation_constraints"]["follow_up"])
        self.assertEqual("英伟达", state["conversation_constraints"]["anchor_entity"])

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

    def test_conversation_resolver_extracts_recent_time_terms(self) -> None:
        node = ConversationResolverNode()
        state = node.run(
            {
                "user_query": "那它今年呢？",
                "messages": [
                    {"role": "user", "content": "英伟达 2025Q4 财报怎么样？"},
                    {"role": "assistant", "content": "2025Q4 表现强劲。"},
                ],
                "current_entities": {"last_entity": "英伟达"},
            }
        )

        self.assertEqual(["2025Q4"], state["conversation_constraints"]["inherited_time_terms"])

    def test_conversation_resolver_normalizes_product_subject_to_company_anchor(self) -> None:
        node = ConversationResolverNode()
        state = node.run({"user_query": "苹果手机近期销量如何"})

        self.assertEqual("苹果手机近期销量如何", state["resolved_user_query"])
        self.assertEqual("苹果", state["current_entities"]["last_entity"])
        self.assertEqual("iPhone", state["current_entities"]["last_product"])
        self.assertEqual("苹果", state["conversation_constraints"]["anchor_entity"])
        self.assertEqual("苹果", state["current_topic"]["entity"])
        self.assertEqual("iPhone", state["current_topic"]["product"])

    def test_conversation_resolver_uses_normalized_company_anchor_for_product_follow_up(self) -> None:
        node = ConversationResolverNode()
        state = node.run(
            {
                "user_query": "那他的其他电子产品呢",
                "messages": [
                    {"role": "user", "content": "苹果手机近期销量如何"},
                    {"role": "assistant", "content": "苹果手机近期销量表现强劲。"},
                ],
                "current_entities": {"last_entity": "苹果", "last_product": "iPhone"},
                "current_topic": {
                    "entity": "苹果",
                    "product": "iPhone",
                    "topic": "苹果手机",
                },
            }
        )

        self.assertEqual("苹果的其他电子产品呢", state["resolved_user_query"])
        self.assertEqual("苹果", state["conversation_constraints"]["anchor_entity"])
        self.assertTrue(state["conversation_constraints"]["follow_up"])
        self.assertEqual(["产品表现"], state["conversation_constraints"]["aspect_hints"])

    def test_conversation_resolver_extracts_metric_hints(self) -> None:
        node = ConversationResolverNode()
        state = node.run({"user_query": "苹果手机近期销量如何"})

        self.assertEqual(["销量"], state["conversation_constraints"]["metric_hints"])
        self.assertEqual(["近期表现"], state["conversation_constraints"]["aspect_hints"])

    def test_conversation_resolver_extracts_comparison_target(self) -> None:
        node = ConversationResolverNode()
        state = node.run(
            {
                "user_query": "那和华为比呢",
                "messages": [
                    {"role": "user", "content": "苹果手机近期销量如何"},
                    {"role": "assistant", "content": "苹果手机近期销量表现强劲。"},
                ],
                "current_entities": {"last_entity": "苹果", "last_product": "iPhone"},
                "current_topic": {
                    "entity": "苹果",
                    "product": "iPhone",
                    "topic": "苹果手机",
                },
            }
        )

        self.assertEqual("华为", state["conversation_constraints"]["comparison_target"])

    def test_conversation_resolver_extracts_output_style_hints(self) -> None:
        node = ConversationResolverNode()
        state = node.run({"user_query": "详细展开说说"})

        self.assertEqual(["detailed"], state["conversation_constraints"]["output_style_hints"])


class RuleEntityResolverTests(unittest.TestCase):
    def test_rule_entity_resolver_normalizes_product_subject(self) -> None:
        resolver = RuleEntityResolver()

        result = resolver.resolve(
            query="苹果手机近期销量如何",
            messages=[],
            current_entities={},
            current_topic={},
        )

        self.assertEqual("苹果", result["primary_entity"])
        self.assertEqual(["苹果"], result["query_entities"])
        self.assertEqual("iPhone", result["topic"]["product"])
        self.assertEqual("苹果手机", result["topic"]["topic"])
        self.assertEqual("rule_alias", result["mentions"][0]["source"])

    def test_rule_entity_resolver_extracts_query_entities_without_alias(self) -> None:
        resolver = RuleEntityResolver()

        result = resolver.resolve(
            query="英伟达近期发展势头如何？",
            messages=[],
            current_entities={},
            current_topic={},
        )

        self.assertEqual("英伟达", result["primary_entity"])
        self.assertEqual(["英伟达"], result["query_entities"])

    def test_conversation_resolver_can_use_injected_entity_resolver(self) -> None:
        resolver = RuleEntityResolver()
        node = ConversationResolverNode(entity_resolver=resolver)

        state = node.run({"user_query": "苹果手机近期销量如何"})

        self.assertEqual("苹果", state["current_entities"]["last_entity"])
        self.assertEqual("iPhone", state["current_entities"]["last_product"])


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

    def test_query_planner_consumes_conversation_constraints(self) -> None:
        node = QueryPlannerNode()
        state = node.run(
            {
                "user_query": "那今年呢？",
                "resolved_user_query": "英伟达今年呢？",
                "current_entities": {
                    "conversation_anchor": "英伟达",
                    "current_query_entities": [],
                },
                "conversation_constraints": {
                    "follow_up": True,
                    "anchor_entity": "英伟达",
                    "inherited_time_terms": ["2025Q4"],
                },
            }
        )

        self.assertIn("follow_up", state["current_sub_intents"])
        self.assertIn("time_inherited", state["current_sub_intents"])
        self.assertEqual(["2025Q4"], state["current_time_range"]["raw_terms"])
        self.assertEqual(["英伟达"], state["retrieval_plan"]["entity_scope"])
        self.assertEqual(
            "英伟达",
            state["retrieval_plan"]["carry_over_constraints"]["anchor_entity"],
        )

    def test_query_planner_preserves_topic_scope(self) -> None:
        node = QueryPlannerNode()
        state = node.run(
            {
                "user_query": "苹果手机近期销量如何",
                "current_entities": {
                    "last_entity": "苹果",
                    "last_product": "iPhone",
                    "current_query_entities": ["苹果"],
                },
                "current_topic": {
                    "entity": "苹果",
                    "product": "iPhone",
                    "topic": "苹果手机",
                },
                "conversation_constraints": {
                    "anchor_entity": "苹果",
                    "normalized_subject": {
                        "entity": "苹果",
                        "product": "iPhone",
                        "topic": "苹果手机",
                    },
                },
            }
        )

        self.assertEqual("苹果", state["retrieval_plan"]["entity_scope"][0])
        self.assertEqual("iPhone", state["retrieval_plan"]["topic_scope"]["product"])

    def test_query_planner_inherits_metric_scope_for_follow_up(self) -> None:
        node = QueryPlannerNode()
        state = node.run(
            {
                "user_query": "那他的其他电子产品呢",
                "resolved_user_query": "苹果的其他电子产品呢",
                "conversation_constraints": {
                    "follow_up": True,
                    "anchor_entity": "苹果",
                    "metric_hints": [],
                    "aspect_hints": ["近期表现"],
                },
                "last_planner_context": {
                    "metric_scope": ["销量"],
                    "aspect_scope": ["近期表现"],
                    "comparison_target": None,
                },
                "current_entities": {"current_query_entities": ["苹果"]},
                "current_topic": {"entity": "苹果", "product": "iPhone", "topic": "苹果手机"},
            }
        )

        self.assertEqual(["销量"], state["retrieval_plan"]["metric_scope"])
        self.assertEqual(["近期表现"], state["retrieval_plan"]["aspect_scope"])

    def test_query_planner_inherits_output_style_for_follow_up(self) -> None:
        node = QueryPlannerNode()
        state = node.run(
            {
                "user_query": "那其他产品呢",
                "resolved_user_query": "苹果其他产品呢",
                "conversation_constraints": {
                    "follow_up": True,
                    "anchor_entity": "苹果",
                    "output_style_hints": [],
                },
                "last_planner_context": {
                    "metric_scope": ["销量"],
                    "aspect_scope": ["近期表现"],
                    "comparison_target": None,
                    "output_style": "list",
                },
                "current_entities": {"current_query_entities": ["苹果"]},
                "current_topic": {"entity": "苹果", "product": "iPhone", "topic": "苹果手机"},
            }
        )

        self.assertEqual("list", state["retrieval_plan"]["output_style"])
        self.assertEqual("list", state["last_planner_context"]["output_style"])

    def test_query_planner_current_output_style_overrides_inherited_style(self) -> None:
        node = QueryPlannerNode()
        state = node.run(
            {
                "user_query": "详细展开说说",
                "resolved_user_query": "苹果详细展开说说",
                "conversation_constraints": {
                    "follow_up": True,
                    "anchor_entity": "苹果",
                    "output_style_hints": ["detailed"],
                },
                "last_planner_context": {
                    "metric_scope": ["销量"],
                    "aspect_scope": ["近期表现"],
                    "comparison_target": None,
                    "output_style": "list",
                },
                "current_entities": {"current_query_entities": ["苹果"]},
                "current_topic": {"entity": "苹果"},
            }
        )

        self.assertEqual("detailed", state["retrieval_plan"]["output_style"])

    def test_query_planner_inherits_comparison_target_for_follow_up(self) -> None:
        node = QueryPlannerNode()
        state = node.run(
            {
                "user_query": "那其他产品呢",
                "resolved_user_query": "苹果其他产品呢",
                "conversation_constraints": {
                    "follow_up": True,
                    "anchor_entity": "苹果",
                    "comparison_target": None,
                },
                "last_planner_context": {
                    "metric_scope": ["销量"],
                    "aspect_scope": ["对比分析"],
                    "comparison_target": "华为",
                },
                "current_entities": {"current_query_entities": ["苹果"]},
                "current_topic": {"entity": "苹果"},
            }
        )

        self.assertEqual("华为", state["retrieval_plan"]["comparison_target"])


class _FakeSearchService:
    embedding_backend = "fake-embedding"

    def __init__(self) -> None:
        self.last_query: str | None = None

    def search_chunks(self, query: str, top_k: int = 10) -> list[dict]:
        from src.domain.models.document import Chunk

        self.last_query = query
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

        self.last_query = query
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
        search_service = _FakeSearchService()
        node = RetrievalStrategistNode(search_service=search_service, default_top_k=2)
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
        self.assertEqual("Sora 2 有什么升级？", search_service.last_query)

    def test_retrieval_strategist_uses_search_service_for_tables(self) -> None:
        search_service = _FakeSearchService()
        node = RetrievalStrategistNode(search_service=search_service, default_top_k=2)
        state = node.run(
            {
                "user_query": "比亚迪 销量",
                "normalized_query": "比亚迪 销量",
                "retrieval_plan": {"top_k": 1, "tables_only": True},
            }
        )

        self.assertEqual(len(state["retrieved_candidates"]), 1)
        self.assertEqual(state["candidate_evidence_types"], ["table_evidence"])
        self.assertEqual("比亚迪 销量", search_service.last_query)

    def test_retrieval_strategist_enriches_follow_up_query_with_plan_scope(self) -> None:
        search_service = _FakeSearchService()
        node = RetrievalStrategistNode(search_service=search_service, default_top_k=2)

        state = node.run(
            {
                "user_query": "那今年呢？",
                "normalized_query": "英伟达今年呢?",
                "retrieval_plan": {
                    "top_k": 2,
                    "tables_only": False,
                    "entity_scope": ["英伟达"],
                    "time_terms": ["2025Q4"],
                },
            }
        )

        self.assertEqual("英伟达今年呢? 2025Q4", search_service.last_query)
        self.assertEqual(search_service.last_query, state["retrieval_query"])

    def test_retrieval_strategist_enriches_query_with_topic_scope(self) -> None:
        search_service = _FakeSearchService()
        node = RetrievalStrategistNode(search_service=search_service, default_top_k=2)

        state = node.run(
            {
                "user_query": "那他的其他电子产品呢",
                "normalized_query": "苹果的其他电子产品呢",
                "retrieval_plan": {
                    "top_k": 2,
                    "tables_only": False,
                    "entity_scope": ["苹果"],
                    "topic_scope": {"product": "iPhone", "topic": "苹果手机"},
                },
            }
        )

        self.assertEqual(
            "苹果的其他电子产品呢 iPhone 苹果手机",
            search_service.last_query,
        )
        self.assertEqual(search_service.last_query, state["retrieval_query"])

    def test_retrieval_strategist_enriches_query_with_metric_scope(self) -> None:
        search_service = _FakeSearchService()
        node = RetrievalStrategistNode(search_service=search_service, default_top_k=2)

        state = node.run(
            {
                "user_query": "苹果的其他电子产品呢",
                "normalized_query": "苹果的其他电子产品呢",
                "retrieval_plan": {
                    "top_k": 2,
                    "tables_only": False,
                    "entity_scope": ["苹果"],
                    "topic_scope": {"product": "iPhone", "topic": "苹果手机"},
                    "metric_scope": ["销量"],
                    "aspect_scope": ["近期表现"],
                },
            }
        )

        self.assertEqual(
            "苹果的其他电子产品呢 iPhone 苹果手机 销量 近期表现",
            search_service.last_query,
        )
        self.assertEqual(search_service.last_query, state["retrieval_query"])


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
