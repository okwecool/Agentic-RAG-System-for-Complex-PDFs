"""Chunking rule defaults."""

from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 100
DEFAULT_MIN_CHUNK_SIZE = 120


@dataclass(slots=True)
class ChunkingConfig:
    target_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_OVERLAP
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE
