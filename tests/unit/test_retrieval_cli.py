import json
import unittest

from src.config.settings import get_settings
from src.retrieval.cli import format_results, run_cli
from src.domain.models.document import Chunk


class RetrievalCliTest(unittest.TestCase):
    def test_format_results_includes_key_fields(self) -> None:
        chunk = Chunk(
            chunk_id="doc_1_p1_c1",
            doc_id="doc_1",
            text="OpenAI 发布 Sora 2，并增强视频生成能力。",
            page_no=1,
            chunk_type="paragraph",
            section_path=["1 Overview"],
            metadata={"page_no": 1},
        )
        output = format_results(
            query="Sora 2",
            results=[
                {
                    "chunk": chunk,
                    "score": 0.1234,
                    "sources": ["bm25", "vector"],
                }
            ],
            preview_chars=80,
        )

        self.assertIn('Query: "Sora 2"', output)
        self.assertIn("doc_1_p1_c1", output)
        self.assertIn("sources=bm25,vector", output)
        self.assertIn("section=1 Overview", output)

    def test_run_cli_loads_chunk_artifacts(self) -> None:
        settings = get_settings()
        chunks_dir = settings.artifacts_dir / "test_cli_chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        try:
            payload = {
                "doc_id": "doc_cli",
                "title": "demo",
                "source_file": "demo.pdf",
                "chunk_count": 2,
                "chunks": [
                    {
                        "chunk_id": "doc_cli_p1_c1",
                        "page_no": 1,
                        "chunk_type": "paragraph",
                        "section_path": ["Document"],
                        "metadata": {"page_no": 1},
                        "text": "OpenAI 发布新一代 Sora 2",
                    },
                    {
                        "chunk_id": "doc_cli_p1_c2",
                        "page_no": 1,
                        "chunk_type": "table",
                        "section_path": ["Document"],
                        "metadata": {"page_no": 1},
                        "text": "比亚迪 销量 份额",
                    },
                ],
            }
            (chunks_dir / "doc_cli.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            output = run_cli(
                query="Sora 2",
                chunks_dir=chunks_dir,
                top_k=1,
                tables_only=False,
                preview_chars=120,
            )
        finally:
            for file_path in chunks_dir.glob("*.json"):
                file_path.unlink()
            chunks_dir.rmdir()

        self.assertIn("doc_cli_p1_c1", output)
        self.assertIn("Hits: 1", output)


if __name__ == "__main__":
    unittest.main()
