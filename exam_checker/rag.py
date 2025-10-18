"""Core retrieval augmented generation pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

from .config import SystemConfig
from .knowledge_base import DocumentChunk, KnowledgeBase

logger = logging.getLogger(__name__)


@dataclass
class LLMClient:
    """Minimal LLM client abstraction.

    The implementation intentionally uses a deterministic heuristic so that the
    system can be executed in environments where external API calls are not
    possible. It summarises the retrieved context and the query to produce a
    human-readable report.
    """

    def generate_report(self, context: Iterable[DocumentChunk], page_text: str) -> str:
        if not page_text.strip():
            return "페이지 텍스트가 비어 있어 검수를 수행할 수 없습니다."

        context_summaries = []
        for chunk in context:
            preview = chunk.text.strip().replace("\n", " ")
            if len(preview) > 180:
                preview = preview[:177] + "..."
            context_summaries.append(
                f"- (p.{chunk.page_number} / #{chunk.chunk_index}) {preview}"
            )
        if not context_summaries:
            context_section = "관련 법규를 찾지 못했습니다."
        else:
            context_section = "\n".join(context_summaries)

        highlighted = self._detect_flags(page_text)

        template = (
            "📄 **페이지 요약**\n"
            f"{page_text[:400].strip()}{'...' if len(page_text) > 400 else ''}\n\n"
            "📚 **참조한 법규 요약**\n"
            f"{context_section}\n\n"
            "⚠️ **검출된 잠재 이슈**\n"
            f"{highlighted if highlighted else '명시적인 위반 사항이 감지되지 않았습니다.'}"
        )
        return template

    def _detect_flags(self, page_text: str) -> str:
        flags: List[str] = []
        lowered = page_text.lower()
        keywords = {
            "기준": "기준",  # simple demonstration keywords
            "벌칙": "벌칙",
            "위반": "위반",
            "제한": "제한",
        }
        for keyword, label in keywords.items():
            if keyword in lowered:
                flags.append(f"- 텍스트에 '{label}' 단어가 포함되어 있습니다. 관련 법령과 세부 조항을 확인하세요.")
        return "\n".join(flags)


@dataclass
class RAGPipeline:
    """High-level orchestration of the retrieval augmented generation process."""

    config: SystemConfig
    knowledge_base: KnowledgeBase
    llm_client: LLMClient = LLMClient()

    def generate_page_report(self, page_text: str) -> str:
        logger.debug("Generating report for page with %s characters", len(page_text))
        retrieved = self.knowledge_base.query(page_text, top_k=self.config.top_k)
        logger.debug("Retrieved %s related law chunks", len(retrieved))
        return self.llm_client.generate_report(retrieved, page_text)
