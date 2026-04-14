import os
import unittest
from pathlib import Path
from uuid import uuid4

from src.config.settings import _load_env_file, _optional_path_from_env, _path_from_env


class SettingsTests(unittest.TestCase):
    def test_load_env_file_sets_missing_values_only(self) -> None:
        env_path = Path("tests") / f".tmp_env_{uuid4().hex}"
        env_path.write_text(
            "DASHSCOPE_API_KEY=test-key\nDASHSCOPE_BASE_URL=https://example.com\n",
            encoding="utf-8",
        )
        original_key = os.environ.pop("DASHSCOPE_API_KEY", None)
        original_url = os.environ.pop("DASHSCOPE_BASE_URL", None)
        try:
            _load_env_file(env_path)
            self.assertEqual("test-key", os.getenv("DASHSCOPE_API_KEY"))
            self.assertEqual("https://example.com", os.getenv("DASHSCOPE_BASE_URL"))
        finally:
            env_path.unlink(missing_ok=True)
            if original_key is None:
                os.environ.pop("DASHSCOPE_API_KEY", None)
            else:
                os.environ["DASHSCOPE_API_KEY"] = original_key
            if original_url is None:
                os.environ.pop("DASHSCOPE_BASE_URL", None)
            else:
                os.environ["DASHSCOPE_BASE_URL"] = original_url

    def test_optional_path_from_env_prefers_env_value(self) -> None:
        original_value = os.environ.get("LOCAL_EMBEDDING_MODEL_DIR")
        try:
            os.environ["LOCAL_EMBEDDING_MODEL_DIR"] = r"D:\Models\demo-embed"
            resolved = _optional_path_from_env(
                "LOCAL_EMBEDDING_MODEL_DIR",
                default=Path(r"E:\Models\bge-base-zh-v1.5"),
            )
            self.assertEqual(Path(r"D:\Models\demo-embed"), resolved)
        finally:
            if original_value is None:
                os.environ.pop("LOCAL_EMBEDDING_MODEL_DIR", None)
            else:
                os.environ["LOCAL_EMBEDDING_MODEL_DIR"] = original_value

    def test_path_from_env_resolves_relative_to_base_dir(self) -> None:
        original_value = os.environ.get("RETRIEVAL_INDEX_DIR")
        try:
            os.environ["RETRIEVAL_INDEX_DIR"] = r"indexes\custom_cache"
            resolved = _path_from_env(
                "RETRIEVAL_INDEX_DIR",
                default=Path("indexes/default"),
                base_dir=Path(r"E:\Project\Agentic_Project\Agentic-RAG-System-for-Complex-PDFs"),
            )
            self.assertEqual(
                Path(r"E:\Project\Agentic_Project\Agentic-RAG-System-for-Complex-PDFs\indexes\custom_cache"),
                resolved,
            )
        finally:
            if original_value is None:
                os.environ.pop("RETRIEVAL_INDEX_DIR", None)
            else:
                os.environ["RETRIEVAL_INDEX_DIR"] = original_value
