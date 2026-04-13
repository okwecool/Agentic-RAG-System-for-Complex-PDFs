"""Ingestion task result models."""

from dataclasses import dataclass


@dataclass(slots=True)
class IngestionResult:
    scanned_files: int = 0
    successful_documents: int = 0
    failed_documents: int = 0

