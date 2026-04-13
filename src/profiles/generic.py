"""Generic profile."""

from src.domain.models.document import Document
from src.profiles.base import BaseProfile


class GenericProfile(BaseProfile):
    name = "generic"

    def detect(self, document: Document) -> bool:
        del document
        return True

