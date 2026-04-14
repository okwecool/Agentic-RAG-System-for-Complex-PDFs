"""Base helpers for embedding providers."""

from __future__ import annotations

from pathlib import Path


class BaseEmbeddingProvider:
    backend = "unknown"

    def save_state(self, output_dir: Path) -> None:
        del output_dir

    def load_state(self, input_dir: Path) -> None:
        del input_dir
