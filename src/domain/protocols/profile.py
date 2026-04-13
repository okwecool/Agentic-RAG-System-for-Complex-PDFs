"""Domain profile protocol."""

from typing import Any, Protocol

from src.domain.models.document import Document


class DomainProfile(Protocol):
    name: str

    def detect(self, document: Document) -> bool:
        """Return whether the profile matches the document."""

    def enrich_metadata(self, document: Document) -> dict[str, Any]:
        """Extract domain metadata."""

    def extract_entities(self, text: str) -> dict[str, Any]:
        """Extract query-side entities."""

    def expand_query(self, query: str, state: dict[str, Any]) -> list[str]:
        """Return expanded query variants."""

    def build_filters(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Build retrieval filters."""

    def build_prompt_context(self) -> dict[str, Any]:
        """Return prompt-time context."""

