"""Answer generation placeholder."""


class AnswerGenerator:
    def generate(self, query: str, evidence: list[dict]) -> dict:
        if not evidence:
            return {
                "answer": "I could not find enough supporting evidence.",
                "claims": [],
                "confidence": "low",
            }
        return {
            "answer": f"Draft answer for: {query}",
            "claims": [
                {
                    "claim": f"Draft answer for: {query}",
                    "supporting_chunk_ids": [
                        item["chunk"].chunk_id for item in evidence if "chunk" in item
                    ],
                }
            ],
            "confidence": "medium",
        }

