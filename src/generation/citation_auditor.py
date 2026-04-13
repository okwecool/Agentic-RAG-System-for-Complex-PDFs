"""Citation audit placeholder."""


class CitationAuditor:
    def audit(self, claims: list[dict], evidence: list[dict]) -> dict:
        chunk_ids = {item["chunk"].chunk_id for item in evidence if "chunk" in item}
        verified_claims = []
        for claim in claims:
            supporting = [
                chunk_id
                for chunk_id in claim.get("supporting_chunk_ids", [])
                if chunk_id in chunk_ids
            ]
            if supporting:
                verified_claims.append(
                    {"claim": claim["claim"], "chunk_ids": supporting}
                )
        return {
            "verified_claims": verified_claims,
            "unsupported_claims": [],
            "citation_map": [],
            "final_confidence": "medium" if verified_claims else "low",
        }

