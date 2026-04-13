import unittest

from src.domain.models.document import Block, Document, Page


class DocumentModelTest(unittest.TestCase):
    def test_document_to_dict_contains_nested_pages(self) -> None:
        document = Document(
            doc_id="doc_test",
            title="Test",
            source_file="test.pdf",
            pages=[
                Page(
                    page_no=1,
                    blocks=[Block(block_id="b1", type="paragraph", text="hello")],
                )
            ],
        )

        payload = document.to_dict()

        self.assertEqual(payload["doc_id"], "doc_test")
        self.assertEqual(payload["pages"][0]["blocks"][0]["text"], "hello")


if __name__ == "__main__":
    unittest.main()

