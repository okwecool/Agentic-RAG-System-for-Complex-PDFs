"""Local file storage helper."""

from pathlib import Path


class FileStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

