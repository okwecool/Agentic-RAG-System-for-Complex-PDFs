from __future__ import annotations

import unittest

from src.frontend.controller import FrontendController
from src.frontend.state import create_session_state


class _FakeQaClient:
    def ask(self, query: str, top_k: int | None = None, tables_only: bool = False, session_id: str | None = None) -> dict:
        return {
            "query": query,
            "answer": "这是一个测试回答。",
            "confidence": "medium",
            "model": "stub-model",
            "prompt_family": "qwen",
            "embedding_backend": "sentence_transformer",
            "retrieved_count": 2,
            "citations": [
                {
                    "claim": "测试 claim",
                    "doc_id": "doc_test",
                    "page_no": 3,
                    "chunk_id": "doc_test_p3_c1",
                    "excerpt": "测试引用摘录",
                }
            ],
            "evidence": [
                {
                    "chunk_id": "doc_test_p3_c1",
                    "doc_id": "doc_test",
                    "page_no": 3,
                    "chunk_type": "paragraph",
                    "section_path": ["测试章节"],
                    "score": 0.9,
                    "sources": ["bm25", "vector"],
                    "text": "测试证据内容",
                }
            ],
        }


class _FailingQaClient:
    def ask(self, query: str, top_k: int | None = None, tables_only: bool = False, session_id: str | None = None) -> dict:
        raise RuntimeError("backend unavailable")


class FrontendControllerTests(unittest.TestCase):
    def test_handle_question_updates_history_and_state(self) -> None:
        controller = FrontendController(_FakeQaClient())

        _, history, state, citations_md, evidence_md, status_md = controller.handle_question(
            query="测试问题",
            chat_history=[],
            session_state=create_session_state(),
            top_k=4,
            tables_only=False,
        )

        self.assertEqual(
            history,
            [
                {"role": "user", "content": "测试问题"},
                {"role": "assistant", "content": "这是一个测试回答。"},
            ],
        )
        self.assertEqual(len(state["messages"]), 2)
        self.assertIn("doc_test", citations_md)
        self.assertIn("测试证据内容", evidence_md)
        self.assertIn("stub-model", status_md)

    def test_handle_question_returns_hint_for_empty_query(self) -> None:
        controller = FrontendController(_FakeQaClient())

        _, history, state, citations_md, evidence_md, status_md = controller.handle_question(
            query="   ",
            chat_history=[],
            session_state=create_session_state(),
            top_k=4,
            tables_only=False,
        )

        self.assertEqual(history, [])
        self.assertEqual(state["messages"], [])
        self.assertIn("请输入问题", status_md)
        self.assertIn("暂无引用", citations_md)
        self.assertIn("暂无证据", evidence_md)

    def test_handle_question_surfaces_backend_error(self) -> None:
        controller = FrontendController(_FailingQaClient())

        _, history, _, _, _, status_md = controller.handle_question(
            query="测试问题",
            chat_history=[],
            session_state=create_session_state(),
            top_k=4,
            tables_only=False,
        )

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertIn("请求失败", status_md)
        self.assertIn("backend unavailable", status_md)


if __name__ == "__main__":
    unittest.main()
