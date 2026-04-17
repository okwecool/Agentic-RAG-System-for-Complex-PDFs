"""Gradio frontend application."""

from __future__ import annotations

from src.config.settings import Settings, get_settings
from src.frontend.controller import FrontendController
from src.frontend.factory import create_qa_client
from src.frontend.state import create_session_state


def create_frontend_app(settings: Settings | None = None):
    try:
        import gradio as gr
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError(
            "gradio is not installed in the current environment. Install project dependencies first."
        ) from exc

    resolved_settings = settings or get_settings()
    controller = FrontendController(create_qa_client(resolved_settings))

    mode_choices = [
        ("标准问答", "standard"),
        ("Agentic 问答", "agentic"),
    ]

    with gr.Blocks(title=resolved_settings.frontend_title) as app:
        gr.Markdown(f"# {resolved_settings.frontend_title}")
        gr.Markdown(
            "本地轻量问答前端，支持标准问答与 agentic 工作流，并展示基础引用溯源。"
        )

        session_state = gr.State(create_session_state())

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="对话", height=560)
                query_box = gr.Textbox(
                    label="问题",
                    placeholder="输入你的问题，例如：Sora 2 有什么升级？",
                    lines=3,
                )
                with gr.Row():
                    submit_button = gr.Button("发送", variant="primary")
                    clear_button = gr.Button("清空对话")
            with gr.Column(scale=2):
                qa_mode = gr.Radio(
                    choices=mode_choices,
                    value=resolved_settings.frontend_default_mode,
                    label="问答模式",
                )
                top_k = gr.Slider(
                    minimum=1,
                    maximum=10,
                    step=1,
                    value=resolved_settings.frontend_default_top_k,
                    label="Top K",
                )
                tables_only = gr.Checkbox(label="仅检索表格", value=False)
                status_md = gr.Markdown(controller.initial_status_markdown())
                trace_md = gr.Markdown(controller.initial_trace_markdown())
                citations_md = gr.Markdown(controller.initial_citations_markdown())
                evidence_md = gr.Markdown(controller.initial_evidence_markdown())

        submit_args = {
            "fn": controller.handle_question,
            "inputs": [query_box, chatbot, session_state, top_k, tables_only, qa_mode],
            "outputs": [
                query_box,
                chatbot,
                session_state,
                citations_md,
                evidence_md,
                status_md,
                trace_md,
            ],
        }
        submit_button.click(**submit_args)
        query_box.submit(**submit_args)

        clear_button.click(
            fn=controller.clear_session,
            outputs=[chatbot, session_state, citations_md, evidence_md, status_md, trace_md],
        )

    return app
