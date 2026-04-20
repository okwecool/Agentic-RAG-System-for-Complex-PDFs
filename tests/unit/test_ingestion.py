import json
import shutil
import unittest
import uuid
from pathlib import Path

from src.chunking.chunker import SectionAwareChunker
from src.config.settings import Settings
from src.domain.models.document import Block, Document, Page
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
                            content_role="heading",
                        ),
                        Block(
                            block_id="b_1_2",
                            type="paragraph",
                            text="This is a sample paragraph.",
                            page_no=1,
                            content_role="narrative_paragraph",
                        ),
                    ],
                )
            ],
        )


class NoOpTableExtractor:
    def extract(self, document: Document) -> Document:
        return document


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
                table_extractor=NoOpTableExtractor(),
            )

            result = pipeline.run()

            self.assertEqual(result.scanned_files, 1)
            self.assertEqual(result.successful_documents, 1)
            self.assertEqual(len(list(parsed_dir.glob("*.json"))), 1)
            self.assertEqual(len(list((artifacts_dir / "chunks").glob("*.json"))), 1)
            self.assertTrue((artifacts_dir / "manifests" / "ingestion_summary.json").exists())
            payload = next(parsed_dir.glob("*.json")).read_text(encoding="utf-8")
            self.assertIn("1 Introduction", payload)

            chunk_payload = json.loads(
                next((artifacts_dir / "chunks").glob("*.json")).read_text(encoding="utf-8")
            )
            self.assertEqual("pdf_corpus", chunk_payload["document_source_type"])
            self.assertEqual("narrative_evidence", chunk_payload["chunks"][0]["evidence_type"])
            self.assertEqual(
                ["heading", "narrative_paragraph"],
                chunk_payload["chunks"][0]["metadata"]["source_roles"],
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_chunker_sets_evidence_type_and_metadata(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            document_source_type="research_report",
            pages=[
                Page(
                    page_no=1,
                    page_profile="narrative",
                    blocks=[
                        Block(
                            block_id="b1",
                            type="paragraph",
                            text="Wrapped paragraph first half",
                            section_path=["Section"],
                            page_no=1,
                            content_role="narrative_paragraph",
                            source_span={"page_profile": "narrative"},
                        ),
                        Block(
                            block_id="b2",
                            type="paragraph",
                            text="continued second half.",
                            section_path=["Section"],
                            page_no=1,
                            content_role="narrative_paragraph",
                            source_span={"page_profile": "narrative"},
                        ),
                    ],
                )
            ],
        )

        chunks = SectionAwareChunker().chunk(document)

        self.assertEqual(len(chunks), 1)
        self.assertEqual("narrative_evidence", chunks[0].evidence_type)
        self.assertEqual("research_report", chunks[0].metadata["document_source_type"])
        self.assertEqual(["narrative_paragraph"], chunks[0].metadata["source_roles"])


if __name__ == "__main__":
    unittest.main()
