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
    indexes_dir: Path
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
        indexes_dir=project_root / "indexes",
        debug=os.getenv("APP_DEBUG", "false").lower() == "true",
    )

