"""Thread state storage helpers."""

from __future__ import annotations

from copy import deepcopy

from src.domain.models.state import ResearchState


class InMemoryThreadStore:
    def __init__(self) -> None:
        self._state: dict[str, ResearchState] = {}

    def get(self, thread_id: str) -> ResearchState:
        return deepcopy(self._state.get(thread_id, {}))

    def put(self, thread_id: str, state: ResearchState) -> None:
        self._state[thread_id] = deepcopy(state)

    def delete(self, thread_id: str) -> None:
        self._state.pop(thread_id, None)

