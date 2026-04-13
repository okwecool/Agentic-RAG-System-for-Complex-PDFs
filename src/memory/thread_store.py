"""Thread state storage placeholder."""

from src.domain.models.state import ResearchState


class InMemoryThreadStore:
    def __init__(self) -> None:
        self._state: dict[str, ResearchState] = {}

    def get(self, thread_id: str) -> ResearchState:
        return self._state.get(thread_id, {})

    def put(self, thread_id: str, state: ResearchState) -> None:
        self._state[thread_id] = state

