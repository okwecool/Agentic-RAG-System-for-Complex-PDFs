"""Frontend controller for Gradio interactions."""

from __future__ import annotations

from src.frontend.clients.base import QaClient
from src.frontend.state import (
    append_assistant_message,
    append_user_message,
    create_session_state,
    reset_session_state,
)


class FrontendController:
    def __init__(self, qa_client: QaClient) -> None:
        self._qa_client = qa_client

    @staticmethod
    def initial_status_markdown() -> str:
        return "### 运行状态\n等待提问。"

    @staticmethod
    def initial_citations_markdown() -> str:
        return "### 引用溯源\n暂无引用。"

    @staticmethod
    def initial_evidence_markdown() -> str:
        return "### 证据预览\n暂无证据。"

    @staticmethod
    def initial_trace_markdown() -> str:
        return "### Agentic 过程\n当前未启用 agentic 过程展示。"

    def clear_session(self) -> tuple[list[dict], dict, str, str, str, str]:
        return (
            [],
            reset_session_state(),
            self.initial_citations_markdown(),
            self.initial_evidence_markdown(),
            self.initial_status_markdown(),
            self.initial_trace_markdown(),
        )

    def handle_question(
        self,
        query: str,
        chat_history: list[dict] | None,
        session_state: dict | None,
        top_k: int,
        tables_only: bool,
        qa_mode: str,
    ) -> tuple[str, list[dict], dict, str, str, str, str]:
        normalized_query = (query or "").strip()
        history = list(chat_history or [])
        state = session_state or create_session_state()
        normalized_mode = (qa_mode or "standard").strip().lower()

        if not normalized_query:
            return (
                "",
                history,
                state,
                self.initial_citations_markdown(),
                self.initial_evidence_markdown(),
                "### 运行状态\n请输入问题后再发送。",
                self.initial_trace_markdown(),
            )

        append_user_message(state, normalized_query)
        state["last_mode"] = normalized_mode

        try:
            result = self._qa_client.ask(
                query=normalized_query,
                top_k=int(top_k),
                tables_only=bool(tables_only),
                session_id=state.get("session_id"),
                qa_mode=normalized_mode,
            )
        except Exception as exc:
            error_message = f"请求失败：{exc}"
            history.append({"role": "user", "content": normalized_query})
            history.append({"role": "assistant", "content": error_message})
            return (
                "",
                history,
                state,
                self.initial_citations_markdown(),
                self.initial_evidence_markdown(),
                f"### 运行状态\n{error_message}",
                self.initial_trace_markdown(),
            )

        if result.get("session_id"):
            state["session_id"] = result["session_id"]

        append_assistant_message(state, result)
        history.append({"role": "user", "content": normalized_query})
        history.append({"role": "assistant", "content": result.get("answer", "")})

        return (
            "",
            history,
            state,
            self._format_citations_markdown(result),
            self._format_evidence_markdown(result),
            self._format_status_markdown(
                result,
                top_k=top_k,
                tables_only=tables_only,
                qa_mode=normalized_mode,
            ),
            self._format_trace_markdown(result, qa_mode=normalized_mode),
        )

    @staticmethod
    def _format_status_markdown(
        result: dict,
        top_k: int,
        tables_only: bool,
        qa_mode: str,
    ) -> str:
        lines = [
            "### 运行状态",
            f"- 模式：`{qa_mode}`",
            f'- 置信度：`{result.get("confidence", "unknown")}`',
            f'- 模型：`{result.get("model") or "unknown"}`',
            f'- Prompt：`{result.get("prompt_family") or "unknown"}`',
            f'- Embedding：`{result.get("embedding_backend") or "unknown"}`',
            f'- 召回数量：`{result.get("retrieved_count", 0)}`',
            f"- Top K：`{top_k}`",
            f"- 仅表格：`{tables_only}`",
        ]
        if result.get("session_id"):
            lines.append(f'- Session：`{result.get("session_id")}`')
        if result.get("turn_index") is not None:
            lines.append(f'- Turn：`{result.get("turn_index")}`')
        if result.get("workflow_status"):
            lines.append(f'- Workflow：`{result.get("workflow_status")}`')
        if result.get("route_type"):
            lines.append(f'- Route：`{result.get("route_type")}`')
        return "\n".join(lines)

    @staticmethod
    def _format_citations_markdown(result: dict) -> str:
        citations = result.get("citations", [])
        if not citations:
            return "### 引用溯源\n暂无引用。"
        lines = ["### 引用溯源"]
        for idx, citation in enumerate(citations, start=1):
            lines.append(
                f'{idx}. `{citation["doc_id"]}` 第 `{citation["page_no"]}` 页 '
                f'`{citation["chunk_id"]}`'
            )
            excerpt = (citation.get("excerpt") or "").strip()
            if excerpt:
                lines.append(f"   {excerpt}")
        return "\n".join(lines)

    @staticmethod
    def _format_evidence_markdown(result: dict) -> str:
        evidence = result.get("evidence", [])
        if not evidence:
            return "### 证据预览\n暂无证据。"
        lines = ["### 证据预览"]
        for idx, item in enumerate(evidence, start=1):
            preview = (item.get("text") or "").strip().replace("\n", " ")
            lines.append(
                f'{idx}. `{item["chunk_type"]}` | 页码 `{item["page_no"]}` | '
                f'分数 `{float(item.get("score", 0.0)):.4f}`'
            )
            if preview:
                lines.append(f"   {preview[:220]}")
        return "\n".join(lines)

    @staticmethod
    def _format_trace_markdown(result: dict, qa_mode: str) -> str:
        if qa_mode != "agentic":
            return "### Agentic 过程\n当前为标准问答模式，未展示路由过程。"

        route_trace = result.get("route_trace") or []
        if not route_trace:
            return "### Agentic 过程\n暂无可展示的工作流轨迹。"

        lines = ["### Agentic 过程"]
        for idx, item in enumerate(route_trace, start=1):
            lines.append(
                f'{idx}. `{item.get("next_node", "unknown")}` '
                f'| reason=`{item.get("reason", "unknown")}` '
                f'| route=`{item.get("route_type", "unknown")}`'
            )
            summary = item.get("node_summary") or {}
            if summary:
                summary_text = ", ".join(f"{key}={value}" for key, value in summary.items())
                lines.append(f"   {summary_text}")

        conversation_summary = result.get("conversation_summary")
        if conversation_summary:
            lines.append("")
            lines.append("### 会话摘要")
            lines.append(conversation_summary)
        return "\n".join(lines)
