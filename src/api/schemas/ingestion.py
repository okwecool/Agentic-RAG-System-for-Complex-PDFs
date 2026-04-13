"""Schemas for ingestion-facing API responses."""

from pydantic import BaseModel, Field


class IngestionRunResponse(BaseModel):
    scanned_files: int = Field(default=0)
    successful_documents: int = Field(default=0)
    failed_documents: int = Field(default=0)

