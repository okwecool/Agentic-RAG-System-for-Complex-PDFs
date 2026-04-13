"""Application settings."""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


@dataclass(slots=True)
class Settings:
    project_root: Path
    data_dir: Path
    source_pdf_dir: Path
    artifacts_dir: Path
    parsed_dir: Path
    chunks_dir: Path
    manifests_dir: Path
    indexes_dir: Path
    local_embedding_model_dir: Path | None = None
    debug: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    artifacts_dir = project_root / "artifacts"
    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        source_pdf_dir=data_dir / "source_pdf",
        artifacts_dir=artifacts_dir,
        parsed_dir=artifacts_dir / "parsed",
        chunks_dir=artifacts_dir / "chunks",
        manifests_dir=artifacts_dir / "manifests",
        indexes_dir=project_root / "indexes",
        local_embedding_model_dir=Path(r"E:\Models\bge-base-zh-v1.5"),
        debug=os.getenv("APP_DEBUG", "false").lower() == "true",
    )
