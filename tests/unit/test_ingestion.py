import unittest
import uuid
import shutil
from pathlib import Path

from src.domain.models.document import Block, Document, Page
from src.chunking.chunker import SectionAwareChunker
from src.config.settings import Settings
from src.ingestion.pipeline import IngestionPipeline


class FakeParser:
    def parse(self, file_path: str) -> Document:
        return Document(
            doc_id="pending",
            title=Path(file_path).stem,
            source_file=file_path,
            pages=[
                Page(
                    page_no=1,
                    blocks=[
                        Block(
                            block_id="b_1_1",
                            type="heading",
                            text="1 Introduction",
                            page_no=1,
                        ),
                        Block(
                            block_id="b_1_2",
                            type="paragraph",
                            text="This is a sample paragraph.",
                            page_no=1,
                        ),
                    ],
                )
            ],
        )


class IngestionPipelineTest(unittest.TestCase):
    def test_run_creates_artifact_for_pdf_file(self) -> None:
        root = Path.cwd() / ".tmp_tests" / str(uuid.uuid4())
        try:
            source_pdf_dir = root / "data" / "source_pdf"
            artifacts_dir = root / "artifacts"
            parsed_dir = artifacts_dir / "parsed"
            indexes_dir = root / "indexes"
            source_pdf_dir.mkdir(parents=True, exist_ok=True)
            (source_pdf_dir / "sample.pdf").write_bytes(b"%PDF-1.4 placeholder")

            settings = Settings(
                project_root=root,
                data_dir=root / "data",
                source_pdf_dir=source_pdf_dir,
                artifacts_dir=artifacts_dir,
                parsed_dir=parsed_dir,
                chunks_dir=artifacts_dir / "chunks",
                manifests_dir=artifacts_dir / "manifests",
                indexes_dir=indexes_dir,
                debug=False,
            )

            pipeline = IngestionPipeline(
                settings=settings,
                parser=FakeParser(),
                chunker=SectionAwareChunker(),
            )

            result = pipeline.run()

            self.assertEqual(result.scanned_files, 1)
            self.assertEqual(result.successful_documents, 1)
            self.assertEqual(len(list(parsed_dir.glob("*.json"))), 1)
            self.assertEqual(len(list((artifacts_dir / "chunks").glob("*.json"))), 1)
            self.assertTrue((artifacts_dir / "manifests" / "ingestion_summary.json").exists())
            payload = next(parsed_dir.glob("*.json")).read_text(encoding="utf-8")
            self.assertIn("1 Introduction", payload)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
