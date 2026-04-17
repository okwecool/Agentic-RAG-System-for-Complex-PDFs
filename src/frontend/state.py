"""State helpers for the frontend chat experience."""

from __future__ import annotations


def create_session_state() -> dict:
    return {
        "session_id": None,
        "messages": [],
        "last_result": None,
    }


def reset_session_state() -> dict:
    return create_session_state()


def append_user_message(state: dict, content: str) -> dict:
    state.setdefault("messages", []).append({"role": "user", "content": content})
    return state


def append_assistant_message(state: dict, result: dict) -> dict:
    state.setdefault("messages", []).append(
        {
            "role": "assistant",
            "content": result.get("answer", ""),
            "citations": result.get("citations", []),
            "metadata": {
                "confidence": result.get("confidence"),
                "model": result.get("model"),
                "prompt_family": result.get("prompt_family"),
                "embedding_backend": result.get("embedding_backend"),
                "retrieved_count": result.get("retrieved_count"),
            },
        }
    )
    state["last_result"] = result
    return state

