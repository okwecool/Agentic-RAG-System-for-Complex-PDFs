from dataclasses import dataclass
import unittest

from src.generation.answer_generator import AnswerGenerator
from src.generation.prompts.qwen import QwenPromptTemplate
from src.generation.qa_service import QaService
from src.generation.citation_auditor import CitationAuditor
from src.retrieval.context_packer import ContextPacker


@dataclass(slots=True)
class FakeChunk:
    chunk_id: str
    doc_id: str
    text: str
    page_no: int
    chunk_type: str
    section_path: list[str]


class FakeLlmProvider:
    backend = "fake"
    model_name = "fake-model"

    def __init__(self) -> None:
        self.last_user_prompt = ""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.last_user_prompt = user_prompt
        return "根据证据，Sora 2 支持原生音视频同步。"


class FakeSearchService:
    embedding_backend = "fake-embedding"

    def __init__(self, results: list[dict]) -> None:
        self._results = results

    def search_chunks(self, query: str, top_k: int = 10) -> list[dict]:
        return self._results[:top_k]

    def search_tables(self, query: str, top_k: int = 10) -> list[dict]:
        return [item for item in self._results if item["chunk"].chunk_type == "table"][:top_k]


class GenerationTests(unittest.TestCase):
    def test_answer_generator_builds_prompt_with_evidence(self) -> None:
        provider = FakeLlmProvider()
        generator = AnswerGenerator(provider, QwenPromptTemplate())
        evidence = [
            {
                "chunk": FakeChunk(
                    chunk_id="c1",
                    doc_id="doc_1",
                    text="Sora 2 首先解决无声局限，实现原生音视频同步。",
                    page_no=5,
                    chunk_type="paragraph",
                    section_path=["2. OpenAI Sora 2 性能实现卓越升级"],
                )
            }
        ]

        result = generator.generate("Sora 2 有什么升级？", evidence)

        self.assertIn("Sora 2 有什么升级", provider.last_user_prompt)
        self.assertIn("原生音视频同步", provider.last_user_prompt)
        self.assertIn("根据当前证据无法确定", provider.last_user_prompt)
        self.assertEqual("fake-model", result["model"])
        self.assertEqual("qwen", result["prompt_family"])

    def test_answer_generator_includes_conversation_context_in_prompt(self) -> None:
        provider = FakeLlmProvider()
        generator = AnswerGenerator(provider, QwenPromptTemplate())
        evidence = [
            {
                "chunk": FakeChunk(
                    chunk_id="c1",
                    doc_id="doc_1",
                    text="苹果销量增长，华为销量回升。",
                    page_no=3,
                    chunk_type="paragraph",
                    section_path=["1. 手机厂商对比"],
                )
            }
        ]

        generator.generate(
            "比起前两个手机厂商，还有哪些值得关注的手机厂商",
            evidence,
            conversation_context={
                "dialogue_referents": ["华为", "苹果"],
                "comparison_target": "苹果",
                "output_style": "list",
            },
        )

        self.assertIn("对话上下文", provider.last_user_prompt)
        self.assertIn("华为", provider.last_user_prompt)
        self.assertIn("苹果", provider.last_user_prompt)
        self.assertIn("list", provider.last_user_prompt)

    def test_answer_generator_adds_prompt_branches_for_dialogue_mode_and_style(self) -> None:
        provider = FakeLlmProvider()
        generator = AnswerGenerator(provider, QwenPromptTemplate())
        evidence = [
            {
                "chunk": FakeChunk(
                    chunk_id="c1",
                    doc_id="doc_1",
                    text="苹果销量增长，华为销量回升。",
                    page_no=3,
                    chunk_type="paragraph",
                    section_path=["1. 手机厂商对比"],
                )
            }
        ]

        generator.generate(
            "比起前两个手机厂商，还有哪些值得关注的手机厂商",
            evidence,
            conversation_context={
                "dialogue_mode": "compare",
                "follow_up": True,
                "dialogue_referents": ["华为", "苹果"],
                "comparison_target": "苹果",
                "output_style": "detailed",
            },
        )

        self.assertIn("这是一个承接上轮上下文的问题", provider.last_user_prompt)
        self.assertIn("请按对比方式组织答案", provider.last_user_prompt)
        self.assertIn("请先给结论，再展开说明", provider.last_user_prompt)

    def test_answer_generator_includes_conversation_summary_in_prompt(self) -> None:
        provider = FakeLlmProvider()
        generator = AnswerGenerator(provider, QwenPromptTemplate())
        evidence = [
            {
                "chunk": FakeChunk(
                    chunk_id="c1",
                    doc_id="doc_1",
                    text="苹果销量增长，华为销量回升。",
                    page_no=3,
                    chunk_type="paragraph",
                    section_path=["1. 手机厂商对比"],
                )
            }
        ]

        generator.generate(
            "那其他产品呢",
            evidence,
            conversation_context={
                "follow_up": True,
                "dialogue_mode": "follow_up",
                "conversation_summary": "user: 苹果手机近期销量如何\nassistant: 苹果手机近期销量表现强劲",
            },
        )

        self.assertIn("会话摘要", provider.last_user_prompt)
        self.assertIn("苹果手机近期销量如何", provider.last_user_prompt)

    def test_qa_service_returns_citations_and_evidence(self) -> None:
        provider = FakeLlmProvider()
        results = [
            {
                "chunk": FakeChunk(
                    chunk_id="c1",
                    doc_id="doc_1",
                    text="Sora 2 首先解决无声局限，实现原生音视频同步。",
                    page_no=5,
                    chunk_type="paragraph",
                    section_path=["2. OpenAI Sora 2 性能实现卓越升级"],
                ),
                "score": 0.8,
                "sources": {"bm25", "vector"},
            }
        ]
        service = QaService(
            search_service=FakeSearchService(results),
            answer_generator=AnswerGenerator(provider, QwenPromptTemplate()),
            citation_auditor=CitationAuditor(),
            context_packer=ContextPacker(),
            top_k=3,
        )

        result = service.answer("Sora 2 有什么升级？")

        self.assertEqual("根据证据，Sora 2 支持原生音视频同步。", result["answer"])
        self.assertEqual("medium", result["confidence"])
        self.assertEqual(1, len(result["citations"]))
        self.assertEqual("c1", result["citations"][0]["chunk_id"])
        self.assertEqual("fake-embedding", result["embedding_backend"])
        self.assertEqual("qwen", result["prompt_family"])
