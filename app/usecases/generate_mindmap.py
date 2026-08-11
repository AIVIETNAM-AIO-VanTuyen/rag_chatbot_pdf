# app/usecases/generate_mindmap.py
"""Usecase: sinh sơ đồ tư duy dạng JSON từ tài liệu đã nạp."""
from typing import Any

from app.domain.errors import MindmapParseError
from app.domain.json_utils import parse_json_object
from app.domain.models import ChatTurn, DocumentRef
from app.domain.ports import EmbeddingProvider, LLMProvider, VectorStore
from app.infra.logging import get_logger
from app.infra.settings import Settings
from app.usecases.prompts import (
    MINDMAP_RETRIEVAL_QUERY,
    MINDMAP_SYSTEM_PROMPT,
    MINDMAP_USER_TEMPLATE,
)
from app.usecases.retrieval import ensure_model_matches, format_context

logger = get_logger("mindmap")


class GenerateMindmap:
    """Lấy các đoạn khái quát của tài liệu rồi nhờ LLM dựng cây sơ đồ."""

    def __init__(
        self,
        *,
        store: VectorStore,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        settings: Settings,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._llm = llm
        self._settings = settings

    def execute(self, ref: DocumentRef) -> dict[str, Any]:
        """Trả về dict sơ đồ tư duy gồm khoá "title" và "nodes"."""
        ensure_model_matches(ref, self._embedder)

        query_vector = self._embedder.embed_query(MINDMAP_RETRIEVAL_QUERY)
        chunks = self._store.search(ref, query_vector, k=self._settings.mindmap_top_k)
        if not chunks:
            raise MindmapParseError("Không lấy được nội dung nào từ tài liệu để dựng sơ đồ.")

        response = self._llm.complete(
            [
                ChatTurn(
                    role="user",
                    content=MINDMAP_USER_TEMPLATE.format(context=format_context(chunks)),
                )
            ],
            system=MINDMAP_SYSTEM_PROMPT,
            temperature=self._settings.mindmap_temperature,
        )

        data = parse_json_object(response)
        if data is None:
            logger.error("LLM trả về nội dung không phải JSON: %r", response[:300])
            raise MindmapParseError(
                "Mô hình không trả về JSON hợp lệ cho sơ đồ tư duy.",
                hint="Hãy bấm Tạo lại sơ đồ, hoặc đổi sang mô hình mạnh hơn.",
            )

        data.setdefault("title", ref.display_name)
        data.setdefault("nodes", [])
        return data
