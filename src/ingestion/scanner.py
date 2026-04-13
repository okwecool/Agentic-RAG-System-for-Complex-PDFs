"""File scanning helpers for PDF ingestion."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(slots=True)
class SourcePdfFile:
    file_path: Path
    file_name: str
    file_hash: str


class PdfScanner:
    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir

    def scan(self) -> list[SourcePdfFile]:
        files: list[SourcePdfFile] = []
        for file_path in sorted(self.source_dir.rglob("*.pdf")):
            files.append(
                SourcePdfFile(
                    file_path=file_path,
                    file_name=file_path.name,
                    file_hash=self._compute_sha256(file_path),
                )
            )
        return files

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        digest = sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

