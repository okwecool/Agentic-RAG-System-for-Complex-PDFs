import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.diagnostics.chunk_audit import ChunkAudit


class ChunkAuditTest(unittest.TestCase):
    def test_audit_flags_heading_heavy_document(self) -> None:
        root = Path.cwd() / ".tmp_tests" / str(uuid.uuid4())
        try:
            chunks_dir = root / "artifacts" / "chunks"
            manifests_dir = root / "artifacts" / "manifests"
            chunks_dir.mkdir(parents=True, exist_ok=True)
            manifests_dir.mkdir(parents=True, exist_ok=True)

            manifest = {
                "documents": [
                    {
                        "doc_id": "doc_test",
                        "source_file": "sample.pdf",
                        "page_count": 2,
                        "chunk_count": 20,
                    }
                ]
            }
            (manifests_dir / "ingestion_summary.json").write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = {
                "doc_id": "doc_test",
                "title": "Sample",
                "source_file": "sample.pdf",
                "chunk_count": 20,
                "chunks": [
                    {
                        "chunk_id": f"c{i}",
                        "page_no": 1,
                        "chunk_type": "heading" if i < 12 else "paragraph",
                        "section_path": ["Doc"],
                        "metadata": {},
                        "text": "x" if i < 10 else "Long enough text",
                    }
                    for i in range(20)
                ],
            }
            (chunks_dir / "doc_test.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            report = ChunkAudit().audit(
                chunks_dir=chunks_dir,
                manifest_path=manifests_dir / "ingestion_summary.json",
            )

            self.assertEqual(report["document_count"], 1)
            self.assertEqual(len(report["alerts"]), 1)
            self.assertIn("high_chunk_page_ratio", report["alerts"][0]["reasons"])
            self.assertIn("high_heading_ratio", report["alerts"][0]["pages"][0]["reasons"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
