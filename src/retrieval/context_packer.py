"""Context assembly helpers."""


class ContextPacker:
    def pack(self, candidates: list[dict], max_items: int = 8) -> list[dict]:
        return candidates[:max_items]

