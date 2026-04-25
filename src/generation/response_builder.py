"""Shared response serialization helpers for QA services."""

from __future__ import annotations

from dataclasses import asdict

from src.domain.models.citation import Citation


def build_citations(claims: list[dict], evidence: list[dict]) -> list[Citation]:
    evidence_by_id = {
        item["chunk"].chunk_id: item["chunk"]
        for item in evidence
        if "chunk" in item
    }
    citations: list[Citation] = []
    seen_chunk_ids: set[str] = set()
    for claim in claims:
        for chunk_id in claim.get("chunk_ids", []):
            if chunk_id in seen_chunk_ids or chunk_id not in evidence_by_id:
                continue
            chunk = evidence_by_id[chunk_id]
            citations.append(
                Citation(
                    claim=claim["claim"],
                    doc_id=chunk.doc_id,
                    page_no=chunk.page_no,
                    chunk_id=chunk.chunk_id,
                    excerpt=chunk.text[:240],
                )
            )
            seen_chunk_ids.add(chunk_id)
    return citations


def serialize_citations(citations: list[Citation]) -> list[dict]:
    return [asdict(citation) for citation in citations]


def serialize_evidence(item: dict) -> dict:
    chunk = item["chunk"]
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "page_no": chunk.page_no,
        "chunk_type": chunk.chunk_type,
        "section_path": chunk.section_path,
        "score": float(item.get("score", 0.0)),
        "sources": sorted(item.get("sources", [])),
        "text": chunk.text,
    }


def serialize_evidence_list(evidence: list[dict]) -> list[dict]:
    return [serialize_evidence(item) for item in evidence]
