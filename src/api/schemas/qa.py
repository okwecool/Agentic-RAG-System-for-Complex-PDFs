"""Schemas for question answering APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QaRequest(BaseModel):
    query: str = Field(min_length=1, description="User question.")
    top_k: int | None = Field(default=None, ge=1, le=20)
    tables_only: bool = False


class CitationResponse(BaseModel):
    claim: str
    doc_id: str
    page_no: int
    chunk_id: str
    excerpt: str | None = None


class EvidenceResponse(BaseModel):
    chunk_id: str
    doc_id: str
    page_no: int
    chunk_type: str
    section_path: list[str]
    score: float
    sources: list[str]
    text: str


class QaResponse(BaseModel):
    query: str
    answer: str
    confidence: str
    model: str | None = None
    prompt_family: str | None = None
    embedding_backend: str
    retrieved_count: int
    workflow_status: str | None = None
    route_type: str | None = None
    citations: list[CitationResponse]
    evidence: list[EvidenceResponse]
