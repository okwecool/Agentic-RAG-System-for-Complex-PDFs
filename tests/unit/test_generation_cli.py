import unittest

from src.generation.cli import format_answer


class GenerationCliTests(unittest.TestCase):
    def test_format_answer_includes_citations_and_evidence(self) -> None:
        result = {
            "query": "Sora 2 有什么升级？",
            "confidence": "medium",
            "model": "qwen-plus",
            "embedding_backend": "sentence_transformer",
            "answer": "Sora 2 支持原生音视频同步。",
            "citations": [
                {
                    "doc_id": "doc_1",
                    "page_no": 5,
                    "chunk_id": "c1",
                    "excerpt": "Sora 2 首先解决无声局限。",
                }
            ],
            "evidence": [
                {
                    "chunk_id": "c1",
                    "chunk_type": "paragraph",
                    "page_no": 5,
                    "score": 0.9,
                    "text": "Sora 2 首先解决无声局限，实现原生音视频同步。",
                }
            ],
        }

        rendered = format_answer(result)

        self.assertIn('Query: "Sora 2 有什么升级？"', rendered)
        self.assertIn("Citations:", rendered)
        self.assertIn("Evidence Preview:", rendered)
        self.assertIn("doc_1 page=5 chunk=c1", rendered)
