import unittest

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - environment-specific dependency
    TestClient = None

try:
    from src.api.app import create_app
    from src.api.routes.qa import get_qa_service
except ModuleNotFoundError:  # pragma: no cover - environment-specific dependency
    create_app = None
    get_qa_service = None


class StubQaService:
    def answer(self, query: str, top_k: int | None = None, tables_only: bool = False) -> dict:
        return {
            "query": query,
            "answer": "测试答案",
            "confidence": "medium",
            "model": "stub-model",
            "embedding_backend": "stub-embedding",
            "retrieved_count": 1,
            "citations": [
                {
                    "claim": "测试答案",
                    "doc_id": "doc_1",
                    "page_no": 2,
                    "chunk_id": "c1",
                    "excerpt": "证据片段",
                }
            ],
            "evidence": [
                {
                    "chunk_id": "c1",
                    "doc_id": "doc_1",
                    "page_no": 2,
                    "chunk_type": "paragraph",
                    "section_path": ["测试章节"],
                    "score": 0.9,
                    "sources": ["bm25"],
                    "text": "证据片段",
                }
            ],
        }


class ApiQaTests(unittest.TestCase):
    @unittest.skipIf(
        TestClient is None or create_app is None,
        "fastapi test client is not installed",
    )
    def test_qa_route_returns_answer_payload(self) -> None:
        app = create_app()
        app.dependency_overrides[get_qa_service] = lambda: StubQaService()
        client = TestClient(app)

        response = client.post("/api/qa/ask", json={"query": "测试问题"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("测试答案", payload["answer"])
        self.assertEqual("stub-model", payload["model"])
        self.assertEqual(1, len(payload["citations"]))
        app.dependency_overrides.clear()
