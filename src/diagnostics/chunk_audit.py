"""Chunk anomaly audit utilities."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import median
from typing import Any


@dataclass(slots=True)
class AuditThresholds:
    doc_ratio_warn: float = 8.0
    doc_ratio_critical: float = 12.0
    page_chunk_warn: int = 18
    page_heading_ratio_warn: float = 0.6
    page_short_chunk_warn: int = 10
    short_chunk_length: int = 24
    single_column_table_warn_rows: int = 5


@dataclass(slots=True)
class PageAlert:
    page_no: int
    chunk_count: int
    heading_ratio: float
    short_chunk_count: int
    dominant_type: str
    reasons: list[str]


@dataclass(slots=True)
class DocumentAlert:
    doc_id: str
    title: str
    source_file: str
    page_count: int
    chunk_count: int
    chunk_page_ratio: float
    reasons: list[str]
    pages: list[PageAlert]


class ChunkAudit:
    def __init__(self, thresholds: AuditThresholds | None = None) -> None:
        self.thresholds = thresholds or AuditThresholds()

    def audit(self, chunks_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
        documents = self._load_manifest(manifest_path)
        chunk_files = sorted(chunks_dir.glob("*.json"))
        alerts: list[DocumentAlert] = []
        ratios: list[float] = []

        for chunk_file in chunk_files:
            payload = json.loads(chunk_file.read_text(encoding="utf-8"))
            doc_meta = documents.get(payload["doc_id"], {})
            page_count = int(doc_meta.get("page_count") or self._infer_page_count(payload))
            chunk_count = int(payload.get("chunk_count", len(payload.get("chunks", []))))
            ratio = chunk_count / max(page_count, 1)
            ratios.append(ratio)
            page_alerts = self._build_page_alerts(payload.get("chunks", []))
            reasons = self._build_doc_reasons(ratio, page_alerts)
            if reasons:
                alerts.append(
                    DocumentAlert(
                        doc_id=payload["doc_id"],
                        title=payload.get("title", payload["doc_id"]),
                        source_file=payload.get("source_file", doc_meta.get("source_file", "")),
                        page_count=page_count,
                        chunk_count=chunk_count,
                        chunk_page_ratio=round(ratio, 2),
                        reasons=reasons,
                        pages=page_alerts,
                    )
                )

        alerts.sort(key=lambda item: item.chunk_page_ratio, reverse=True)
        summary = {
            "document_count": len(chunk_files),
            "ratio_summary": self._build_ratio_summary(ratios),
            "alerts": [
                {
                    **asdict(alert),
                    "pages": [asdict(page) for page in alert.pages],
                }
                for alert in alerts
            ],
        }
        return summary

    def _load_manifest(self, manifest_path: Path | None) -> dict[str, dict[str, Any]]:
        if manifest_path is None or not manifest_path.exists():
            return {}
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {item["doc_id"]: item for item in payload.get("documents", [])}

    @staticmethod
    def _infer_page_count(payload: dict[str, Any]) -> int:
        pages = [chunk.get("page_no", 0) for chunk in payload.get("chunks", [])]
        return max(pages, default=0)

    def _build_page_alerts(self, chunks: list[dict[str, Any]]) -> list[PageAlert]:
        by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for chunk in chunks:
            by_page[int(chunk["page_no"])].append(chunk)

        alerts: list[PageAlert] = []
        for page_no, page_chunks in sorted(by_page.items()):
            type_counter = Counter(chunk["chunk_type"] for chunk in page_chunks)
            chunk_count = len(page_chunks)
            heading_count = type_counter.get("heading", 0)
            heading_ratio = heading_count / max(chunk_count, 1)
            short_chunk_count = sum(
                1
                for chunk in page_chunks
                if len(chunk.get("text", "").strip()) <= self.thresholds.short_chunk_length
            )
            reasons: list[str] = []
            if chunk_count >= self.thresholds.page_chunk_warn:
                reasons.append("high_page_chunk_count")
            if heading_ratio >= self.thresholds.page_heading_ratio_warn:
                reasons.append("high_heading_ratio")
            if short_chunk_count >= self.thresholds.page_short_chunk_warn:
                reasons.append("many_short_chunks")
            if self._has_suspicious_single_column_table(page_chunks):
                reasons.append("single_column_table_like_text")
            if reasons:
                alerts.append(
                    PageAlert(
                        page_no=page_no,
                        chunk_count=chunk_count,
                        heading_ratio=round(heading_ratio, 2),
                        short_chunk_count=short_chunk_count,
                        dominant_type=type_counter.most_common(1)[0][0],
                        reasons=reasons,
                    )
                )
        alerts.sort(key=lambda item: (item.chunk_count, item.heading_ratio), reverse=True)
        return alerts

    def _has_suspicious_single_column_table(self, page_chunks: list[dict[str, Any]]) -> bool:
        for chunk in page_chunks:
            if chunk.get("chunk_type") != "table":
                continue
            text = chunk.get("text", "")
            lines = [line for line in text.splitlines() if line.strip()]
            if len(lines) < self.thresholds.single_column_table_warn_rows:
                continue
            if all("|" not in line or line.count("|") <= 1 for line in lines):
                return True
        return False

    def _build_doc_reasons(self, ratio: float, page_alerts: list[PageAlert]) -> list[str]:
        reasons: list[str] = []
        if ratio >= self.thresholds.doc_ratio_critical:
            reasons.append("critical_chunk_page_ratio")
        elif ratio >= self.thresholds.doc_ratio_warn:
            reasons.append("high_chunk_page_ratio")

        if sum("high_heading_ratio" in page.reasons for page in page_alerts) >= 2:
            reasons.append("repeated_heading_heavy_pages")
        if sum("many_short_chunks" in page.reasons for page in page_alerts) >= 2:
            reasons.append("repeated_short_chunk_pages")
        if any("single_column_table_like_text" in page.reasons for page in page_alerts):
            reasons.append("suspicious_table_detection")
        return reasons

    @staticmethod
    def _build_ratio_summary(ratios: list[float]) -> dict[str, float]:
        if not ratios:
            return {"min": 0.0, "p50": 0.0, "mean": 0.0, "max": 0.0}
        return {
            "min": round(min(ratios), 2),
            "p50": round(median(ratios), 2),
            "mean": round(sum(ratios) / len(ratios), 2),
            "max": round(max(ratios), 2),
        }


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    chunks_dir = project_root / "artifacts" / "chunks"
    manifests_dir = project_root / "artifacts" / "manifests"
    manifest_path = manifests_dir / "ingestion_summary.json"
    output_path = manifests_dir / "chunk_audit_report.json"

    audit = ChunkAudit()
    report = audit.audit(chunks_dir=chunks_dir, manifest_path=manifest_path)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

