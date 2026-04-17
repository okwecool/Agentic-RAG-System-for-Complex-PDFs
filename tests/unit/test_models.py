import unittest

from src.domain.models.document import Block, Chunk, Document, Page
from src.domain.models.routing import RouteDecision
from src.domain.models.state import ResearchState


class DocumentModelTest(unittest.TestCase):
    def test_document_to_dict_contains_nested_pages(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            document_source_type="research_report",
            pages=[
                Page(
                    page_no=1,
                    page_profile="narrative",
                    blocks=[
                        Block(
                            block_id="b1",
                            type="paragraph",
                            text="hello",
                            content_role="narrative_paragraph",
                            role_confidence=0.9,
                        )
                    ],
                )
            ],
            chunks=[
                Chunk(
                    chunk_id="c1",
                    doc_id="doc_test",
                    text="hello",
                    page_no=1,
                    evidence_type="narrative_evidence",
                )
            ],
        )

        payload = document.to_dict()

        self.assertEqual(payload["doc_id"], "doc_test")
        self.assertEqual(payload["pages"][0]["blocks"][0]["text"], "hello")
        self.assertEqual(payload["document_source_type"], "research_report")
        self.assertEqual(payload["pages"][0]["page_profile"], "narrative")
        self.assertEqual(payload["pages"][0]["blocks"][0]["content_role"], "narrative_paragraph")
        self.assertEqual(payload["chunks"][0]["evidence_type"], "narrative_evidence")

    def test_route_decision_typed_dict_shape(self) -> None:
        decision: RouteDecision = {
            "next_node": "retrieval_strategist",
            "reason": "missing_evidence",
            "route_type": "retrieve_then_synthesize",
            "should_continue": True,
        }

        self.assertEqual(decision["next_node"], "retrieval_strategist")
        self.assertTrue(decision["should_continue"])

    def test_research_state_supports_agentic_fields(self) -> None:
        state: ResearchState = {
            "user_query": "Sora 2 有什么升级？",
            "workflow_status": "running",
            "route_decision": {
                "next_node": "query_planner",
                "reason": "missing_plan",
                "route_type": "plan_then_retrieve",
                "should_continue": True,
            },
            "candidate_evidence_types": ["caption_evidence", "navigational_evidence"],
            "selected_evidence_types": ["narrative_evidence"],
            "retry_count": 1,
            "max_retry_count": 3,
            "document_source_types": ["research_report"],
        }

        self.assertEqual(state["workflow_status"], "running")
        self.assertEqual(state["route_decision"]["next_node"], "query_planner")
        self.assertEqual(state["selected_evidence_types"][0], "narrative_evidence")


if __name__ == "__main__":
    unittest.main()

