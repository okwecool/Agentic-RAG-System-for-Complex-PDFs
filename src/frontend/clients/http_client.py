"""HTTP client for talking to the existing QA APIs."""

from __future__ import annotations

import json
from urllib import error, request


class HttpQaClient:
    def __init__(self, base_url: str, timeout_seconds: float = 120.0) -> None:
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/qa"):
            normalized = f"{normalized}/qa"
        self._ask_url = f"{normalized}/ask"
        self._ask_agentic_url = f"{normalized}/ask-agentic"
        self._timeout_seconds = timeout_seconds

    def ask(
        self,
        query: str,
        top_k: int | None = None,
        tables_only: bool = False,
        session_id: str | None = None,
        qa_mode: str = "standard",
    ) -> dict:
        payload = {
            "query": query,
            "top_k": top_k,
            "tables_only": tables_only,
            "session_id": session_id,
        }
        url = self._ask_agentic_url if qa_mode == "agentic" else self._ask_url
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - depends on runtime API
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"QA API request failed with status {exc.code}: {detail}") from exc
        except error.URLError as exc:  # pragma: no cover - depends on runtime network
            raise RuntimeError(f"Unable to reach QA API: {exc.reason}") from exc
