from __future__ import annotations

import unittest

from src.generation.agentic_qa_service import AgenticQaService
from src.memory.summarizer import ConversationSummarizer
from src.memory.thread_store import InMemoryThreadStore


class _StubWorkflow:
    def __init__(self) -> None:
        self.last_initial_state: dict | None = None

    def run(self, initial_state: dict) -> dict:
        self.last_initial_state = dict(initial_state)
        query = initial_state["user_query"]
        messages = list(initial_state.get("messages", []))
        return {
            "session_id": initial_state.get("session_id"),
            "thread_id": initial_state.get("thread_id"),
            "turn_index": initial_state.get("turn_index"),
            "user_query": query,
            "messages": messages,
            "current_entities": {"current_query_entities": ["英伟达"]} if "英伟达" in query else {},
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
                    "next_node": "conversation_resolver",
                    "reason": "missing_conversation_resolution",
                    "route_type": "resolve_then_plan",
                    "node_summary": {"message_count": len(messages)},
                },
                {
                    "step": 2,
                    "next_node": "finish",
                    "reason": "workflow_complete",
                    "route_type": "finish",
                    "node_summary": {"workflow_status": "completed"},
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
        workflow = _StubWorkflow()
        service = AgenticQaService(
            workflow=workflow,
            thread_store=InMemoryThreadStore(),
            summarizer=ConversationSummarizer(),
            top_k=3,
        )

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
        self.assertEqual("conversation_resolver", result["route_trace"][0]["next_node"])
        self.assertTrue(result["session_id"])
        self.assertEqual(1, result["turn_index"])
        self.assertEqual(
            {"top_k": 3, "tables_only": False},
            workflow.last_initial_state["request_options"],
        )
        self.assertNotIn("retrieval_plan", workflow.last_initial_state)

    def test_agentic_qa_service_persists_session_state_between_turns(self) -> None:
        workflow = _StubWorkflow()
        thread_store = InMemoryThreadStore()
        service = AgenticQaService(
            workflow=workflow,
            thread_store=thread_store,
            summarizer=ConversationSummarizer(),
            top_k=3,
        )

        first = service.answer("英伟达近期发展势头如何？", session_id="session-1")
        second = service.answer("那它今年呢？", session_id="session-1")

        self.assertEqual("session-1", first["session_id"])
        self.assertEqual("session-1", second["session_id"])
        self.assertEqual(2, second["turn_index"])
        persisted = thread_store.get("session-1")
        self.assertEqual(4, len(persisted["messages"]))
        self.assertIn("user: 英伟达近期发展势头如何？", persisted["conversation_summary"])
        self.assertIn("assistant: 这是 agentic 测试答案。", persisted["conversation_summary"])
        self.assertEqual("英伟达", persisted["current_entities"]["last_entity"])


if __name__ == "__main__":
    unittest.main()
