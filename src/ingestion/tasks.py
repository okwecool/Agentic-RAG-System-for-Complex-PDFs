"""Ingestion task result models."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class IngestedDocumentSummary:
    doc_id: str
    source_file: str
    page_count: int
    chunk_count: int
    status: str
    error: str | None = None


@dataclass(slots=True)
class IngestionResult:
    scanned_files: int = 0
    successful_documents: int = 0
    failed_documents: int = 0
    documents: list[IngestedDocumentSummary] = field(default_factory=list)
