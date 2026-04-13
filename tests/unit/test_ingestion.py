import unittest
import uuid
import shutil
from pathlib import Path

from src.chunking.chunker import SectionAwareChunker
from src.config.settings import Settings
from src.ingestion.pipeline import IngestionPipeline
from src.parsing.pymupdf_parser import PyMuPdfParser


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
                indexes_dir=indexes_dir,
                debug=False,
            )

            pipeline = IngestionPipeline(
                settings=settings,
                parser=PyMuPdfParser(),
                chunker=SectionAwareChunker(),
            )

            result = pipeline.run()

            self.assertEqual(result.scanned_files, 1)
            self.assertEqual(result.successful_documents, 1)
            self.assertEqual(len(list(parsed_dir.glob("*.json"))), 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
