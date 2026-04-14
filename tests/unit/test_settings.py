import os
import unittest
from pathlib import Path
from uuid import uuid4

from src.config.settings import _load_env_file


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
