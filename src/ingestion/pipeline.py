"""Top-level ingestion orchestration."""

import json
from pathlib import Path

from src.config.settings import Settings
from src.domain.models.document import Document
from src.domain.protocols.chunker import Chunker
from src.domain.protocols.parser import Parser
from src.ingestion.scanner import PdfScanner
from src.ingestion.tasks import IngestionResult
from src.utils.ids import build_doc_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IngestionPipeline:
    def __init__(self, settings: Settings, parser: Parser, chunker: Chunker) -> None:
        self.settings = settings
        self.parser = parser
        self.chunker = chunker

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
                document.chunks = self.chunker.chunk(document)
                self._write_parsed_document(document)
                result.successful_documents += 1
            except Exception:  # pragma: no cover - detailed handling later
                logger.exception("Failed to ingest %s", source_file.file_path)
                result.failed_documents += 1

        return result

    def _ensure_directories(self) -> None:
        self.settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.settings.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.settings.indexes_dir.mkdir(parents=True, exist_ok=True)

    def _write_parsed_document(self, document: Document) -> None:
        output_path = self.settings.parsed_dir / f"{document.doc_id}.json"
        output_path.write_text(
            json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

