from __future__ import annotations

import unittest

from src.generation.agentic_qa_service import AgenticQaService


class _StubWorkflow:
    def run(self, initial_state: dict) -> dict:
        query = initial_state["user_query"]
        return {
            "user_query": query,
            "draft_answer": "这是 agentic 测试答案。",
            "confidence": "medium",
            "model": "stub-model",
            "prompt_family": "qwen",
            "embedding_backend": "stub-embedding",
            "retrieved_candidates": [
                {
                    "chunk": _StubChunk(),
                    "score": 0.8,
                    "sources": ["bm25"],
                }
            ],
            "selected_evidence": [
                {
                    "chunk": _StubChunk(),
                    "score": 0.8,
                    "sources": ["bm25"],
                }
            ],
            "citation_map": [
                {
                    "claim": "这是 agentic 测试答案。",
                    "chunk_ids": ["c1"],
                }
            ],
            "workflow_status": "completed",
            "route_decision": {"route_type": "audit"},
            "route_trace": [
                {
                    "step": 1,
                    "next_node": "query_planner",
                    "reason": "missing_plan",
                    "route_type": "plan_then_retrieve",
                    "node_summary": {
                        "intent": "summary",
                        "top_k": 3,
                    },
                },
                {
                    "step": 2,
                    "next_node": "finish",
                    "reason": "workflow_complete",
                    "route_type": "finish",
                    "node_summary": {
                        "workflow_status": "completed",
                    },
                },
            ],
        }


class _StubChunk:
    chunk_id = "c1"
    doc_id = "doc_1"
    page_no = 2
    chunk_type = "paragraph"
    section_path = ["测试章节"]
    text = "证据片段"


class AgenticQaServiceTests(unittest.TestCase):
    def test_agentic_qa_service_serializes_workflow_output(self) -> None:
        service = AgenticQaService(workflow=_StubWorkflow(), top_k=3)

        result = service.answer("测试问题")

        self.assertEqual("这是 agentic 测试答案。", result["answer"])
        self.assertEqual("medium", result["confidence"])
        self.assertEqual("stub-model", result["model"])
        self.assertEqual("qwen", result["prompt_family"])
        self.assertEqual("stub-embedding", result["embedding_backend"])
        self.assertEqual("completed", result["workflow_status"])
        self.assertEqual("audit", result["route_type"])
        self.assertEqual(1, len(result["citations"]))
        self.assertEqual(1, len(result["evidence"]))
        self.assertEqual(2, len(result["route_trace"]))
        self.assertEqual("query_planner", result["route_trace"][0]["next_node"])


if __name__ == "__main__":
    unittest.main()
