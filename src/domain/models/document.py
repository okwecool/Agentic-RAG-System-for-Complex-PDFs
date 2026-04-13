"""Structured document models used across the pipeline."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Block:
    block_id: str
    type: str
    text: str
    bbox: tuple[float, float, float, float] | None = None
    section_path: list[str] = field(default_factory=list)
    page_no: int | None = None
    table_html: str | None = None
    table_json: dict[str, Any] | None = None
    source_span: dict[str, Any] | None = None


@dataclass(slots=True)
class Page:
    page_no: int
    blocks: list[Block] = field(default_factory=list)
    width: float | None = None
    height: float | None = None


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    page_no: int
    chunk_type: str = "paragraph"
    section_path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Document:
    doc_id: str
    title: str
    source_file: str
    doc_type: str = "other"
    domain_profile: str = "generic"
    pages: list[Page] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(
        default_factory=lambda: {"generic": {}, "domain": {}}
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
