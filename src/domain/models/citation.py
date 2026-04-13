"""Citation models."""

from dataclasses import dataclass


@dataclass(slots=True)
class Citation:
    claim: str
    doc_id: str
    page_no: int
    chunk_id: str
    excerpt: str | None = None

