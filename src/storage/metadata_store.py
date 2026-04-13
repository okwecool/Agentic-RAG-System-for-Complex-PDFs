"""Metadata storage placeholder."""


class InMemoryMetadataStore:
    def __init__(self) -> None:
        self._documents: dict[str, dict] = {}

    def put(self, doc_id: str, metadata: dict) -> None:
        self._documents[doc_id] = metadata

    def get(self, doc_id: str) -> dict | None:
        return self._documents.get(doc_id)

