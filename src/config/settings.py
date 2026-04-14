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
    retrieval_index_dir: Path | None = None
    local_reranker_model_dir: Path | None = None
    fusion_mode: str = "rrf"
    fusion_rrf_k: int = 60
    fusion_bm25_weight: float = 1.0
    fusion_vector_weight: float = 1.0
    reranker_provider: str = "noop"
    reranker_top_n: int = 20
    reranker_batch_size: int = 8
    llm_provider: str = "openai_compatible"
    llm_prompt_family: str = "auto"
    llm_model_name: str = "qwen-plus"
    dashscope_api_key: str | None = None
    dashscope_base_url: str | None = None
    qa_top_k: int = 6
    debug: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    _load_env_file(project_root / ".env")
    data_dir = _path_from_env("DATA_DIR", default=project_root / "data", base_dir=project_root)
    artifacts_dir = _path_from_env(
        "ARTIFACTS_DIR",
        default=project_root / "artifacts",
        base_dir=project_root,
    )
    indexes_dir = _path_from_env(
        "INDEXES_DIR",
        default=project_root / "indexes",
        base_dir=project_root,
    )
    retrieval_index_dir = _path_from_env(
        "RETRIEVAL_INDEX_DIR",
        default=indexes_dir / "retrieval_cache" / "bge_base_zh_v1_5",
        base_dir=project_root,
    )
    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        source_pdf_dir=_path_from_env(
            "SOURCE_PDF_DIR",
            default=data_dir / "source_pdf",
            base_dir=project_root,
        ),
        artifacts_dir=artifacts_dir,
        parsed_dir=_path_from_env(
            "PARSED_DIR",
            default=artifacts_dir / "parsed",
            base_dir=project_root,
        ),
        chunks_dir=_path_from_env(
            "CHUNKS_DIR",
            default=artifacts_dir / "chunks",
            base_dir=project_root,
        ),
        manifests_dir=_path_from_env(
            "MANIFESTS_DIR",
            default=artifacts_dir / "manifests",
            base_dir=project_root,
        ),
        indexes_dir=indexes_dir,
        local_embedding_model_dir=_optional_path_from_env(
            "LOCAL_EMBEDDING_MODEL_DIR",
            default=None,
            base_dir=project_root,
        ),
        retrieval_index_dir=retrieval_index_dir,
        local_reranker_model_dir=_optional_path_from_env(
            "LOCAL_RERANKER_MODEL_DIR",
            default=None,
            base_dir=project_root,
        ),
        fusion_mode=os.getenv("FUSION_MODE", "rrf"),
        fusion_rrf_k=int(os.getenv("FUSION_RRF_K", "60")),
        fusion_bm25_weight=float(os.getenv("FUSION_BM25_WEIGHT", "1.0")),
        fusion_vector_weight=float(os.getenv("FUSION_VECTOR_WEIGHT", "1.0")),
        reranker_provider=os.getenv("RERANKER_PROVIDER", "noop"),
        reranker_top_n=int(os.getenv("RERANKER_TOP_N", "20")),
        reranker_batch_size=int(os.getenv("RERANKER_BATCH_SIZE", "8")),
        llm_provider=os.getenv("LLM_PROVIDER", "openai_compatible"),
        llm_prompt_family=os.getenv("LLM_PROMPT_FAMILY", "auto"),
        llm_model_name=os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        dashscope_base_url=os.getenv("DASHSCOPE_BASE_URL"),
        qa_top_k=int(os.getenv("QA_TOP_K", "6")),
        debug=os.getenv("APP_DEBUG", "false").lower() == "true",
    )


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        cleaned = value.strip().strip('"').strip("'")
        os.environ[key] = cleaned


def _optional_path_from_env(
    name: str,
    default: Path | None = None,
    base_dir: Path | None = None,
) -> Path | None:
    raw_value = os.getenv(name)
    if raw_value:
        return _resolve_path(Path(raw_value), base_dir=base_dir)
    return default


def _path_from_env(name: str, default: Path, base_dir: Path | None = None) -> Path:
    raw_value = os.getenv(name)
    if raw_value:
        return _resolve_path(Path(raw_value), base_dir=base_dir)
    return default


def _resolve_path(path: Path, base_dir: Path | None = None) -> Path:
    if path.is_absolute() or base_dir is None:
        return path
    return base_dir / path
