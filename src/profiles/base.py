"""Base profile implementation."""

from src.domain.models.document import Document


class BaseProfile:
    name = "base"

    def detect(self, document: Document) -> bool:
        del document
        return False

    def enrich_metadata(self, document: Document) -> dict:
        del document
        return {}

    def extract_entities(self, text: str) -> dict:
        del text
        return {}

    def expand_query(self, query: str, state: dict) -> list[str]:
        del state
        return [query]

    def build_filters(self, plan: dict) -> dict:
        del plan
        return {}

    def build_prompt_context(self) -> dict:
        return {}

