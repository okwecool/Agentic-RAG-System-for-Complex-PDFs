"""Top-level ingestion orchestration."""

import json
from dataclasses import asdict

from src.config.settings import Settings
from src.domain.models.document import Document
from src.domain.protocols.chunker import Chunker
from src.domain.protocols.parser import Parser
from src.ingestion.scanner import PdfScanner
from src.ingestion.tasks import IngestedDocumentSummary, IngestionResult
from src.parsing.cleaner import DocumentCleaner
from src.parsing.section_builder import SectionBuilder
from src.parsing.table_extractor import TableExtractor
from src.utils.ids import build_doc_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        settings: Settings,
        parser: Parser,
        chunker: Chunker,
        cleaner: DocumentCleaner | None = None,
        section_builder: SectionBuilder | None = None,
        table_extractor: TableExtractor | None = None,
    ) -> None:
        self.settings = settings
        self.parser = parser
        self.chunker = chunker
        self.cleaner = cleaner or DocumentCleaner()
        self.section_builder = section_builder or SectionBuilder()
        self.table_extractor = table_extractor or TableExtractor()

    def run(self) -> IngestionResult:
        self._ensure_directories()
        scanner = PdfScanner(self.settings.source_pdf_dir)
        source_files = scanner.scan()
        result = IngestionResult(scanned_files=len(source_files))

        for source_file in source_files:
            try:
                document = self.parser.parse(str(source_file.file_path))
                document.doc_id = build_doc_id(
                    source_file.file_name,
                    source_file.file_hash,
                )
                document.source_file = str(source_file.file_path)
                document.metadata.setdefault("generic", {})
                document.metadata["generic"]["file_hash"] = source_file.file_hash
                document.metadata["generic"]["file_name"] = source_file.file_name
                document = self.cleaner.clean(document)
                document = self.section_builder.apply(document)
                document = self.table_extractor.extract(document)
                document = self.section_builder.apply(document)
                document.metadata["generic"]["page_count"] = len(document.pages)
                document.chunks = self.chunker.chunk(document)
                self._write_parsed_document(document)
                self._write_chunk_document(document)
                result.documents.append(
                    IngestedDocumentSummary(
                        doc_id=document.doc_id,
                        source_file=document.source_file,
                        page_count=len(document.pages),
                        chunk_count=len(document.chunks),
                        status="success",
                    )
                )
                result.successful_documents += 1
            except Exception:  # pragma: no cover - detailed handling later
                logger.exception("Failed to ingest %s", source_file.file_path)
                result.documents.append(
                    IngestedDocumentSummary(
                        doc_id=build_doc_id(source_file.file_name, source_file.file_hash),
                        source_file=str(source_file.file_path),
                        page_count=0,
                        chunk_count=0,
                        status="failed",
                        error="ingestion_error",
                    )
                )
                result.failed_documents += 1

        self._write_manifest(result)
        return result

    def _ensure_directories(self) -> None:
        self.settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.settings.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.settings.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.settings.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.settings.indexes_dir.mkdir(parents=True, exist_ok=True)

    def _write_parsed_document(self, document: Document) -> None:
        output_path = self.settings.parsed_dir / f"{document.doc_id}.json"
        output_path.write_text(
            json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_chunk_document(self, document: Document) -> None:
        output_path = self.settings.chunks_dir / f"{document.doc_id}.json"
        payload = {
            "doc_id": document.doc_id,
            "title": document.title,
            "source_file": document.source_file,
            "chunk_count": len(document.chunks),
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "page_no": chunk.page_no,
                    "chunk_type": chunk.chunk_type,
                    "section_path": chunk.section_path,
                    "metadata": chunk.metadata,
                    "text": chunk.text,
                }
                for chunk in document.chunks
            ],
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_manifest(self, result: IngestionResult) -> None:
        output_path = self.settings.manifests_dir / "ingestion_summary.json"
        payload = {
            "scanned_files": result.scanned_files,
            "successful_documents": result.successful_documents,
            "failed_documents": result.failed_documents,
            "documents": [asdict(item) for item in result.documents],
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
