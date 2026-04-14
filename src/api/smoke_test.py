"""Simple HTTP smoke test for the QA API."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def _request_json(url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset)
        return response.status, json.loads(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a smoke test against the QA API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--query", default="Sora 2 有什么升级？")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--tables-only", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        health_status, health_payload = _request_json(f"{base_url}/api/health")
        qa_status, qa_payload = _request_json(
            f"{base_url}/api/qa/ask",
            {
                "query": args.query,
                "top_k": args.top_k,
                "tables_only": args.tables_only,
            },
        )
    except urllib.error.URLError as exc:  # pragma: no cover - integration helper
        raise SystemExit(f"Failed to reach API server: {exc}") from exc

    print(f"Health status: {health_status}")
    print(json.dumps(health_payload, ensure_ascii=False, indent=2))
    print()
    print(f"QA status: {qa_status}")
    print(json.dumps(qa_payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
