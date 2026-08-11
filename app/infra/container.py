# app/infra/container.py
"""Lắp ráp phụ thuộc cho toàn ứng dụng.

Thay cho các singleton kiểu `ai_service = AIService()` khởi tạo ngay lúc import
ở bản cũ. Với container, mọi thành phần được dựng lười và inject vào nhau, nên
test có thể thay bất kỳ mảnh nào bằng đối tượng giả.
"""
from functools import cached_property

from app.adapters.chroma_store import ChromaVectorStore
from app.adapters.gemini_provider import GeminiEmbeddingProvider, GeminiLLMProvider
from app.adapters.pdf_loader import PyPdfLoader
from app.infra.logging import setup_logging
from app.infra.settings import Settings, get_settings
from app.usecases.answer_question import AnswerQuestion
from app.usecases.generate_mindmap import GenerateMindmap
from app.usecases.ingest_document import IngestDocument


class Container:
    """Giữ và tạo lười các thành phần dùng chung của ứng dụng."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        setup_logging(self.settings.log_level)

    # -- Hạ tầng ------------------------------------------------------------

    @cached_property
    def store(self) -> ChromaVectorStore:
        return ChromaVectorStore(self.settings)

    @cached_property
    def loader(self) -> PyPdfLoader:
        return PyPdfLoader(self.settings)

    @cached_property
    def embedder(self) -> GeminiEmbeddingProvider:
        return GeminiEmbeddingProvider(self.settings)

    @cached_property
    def llm(self) -> GeminiLLMProvider:
        return GeminiLLMProvider(self.settings)

    @property
    def is_ready(self) -> bool:
        """Đã cấu hình đủ để phục vụ chưa (dùng cho thông báo trên UI)."""
        return self.embedder.is_available()

    # -- Usecase --------------------------------------------------------------

    @cached_property
    def ingest_document(self) -> IngestDocument:
        return IngestDocument(
            loader=self.loader,
            store=self.store,
            embedder=self.embedder,
            settings=self.settings,
        )

    @cached_property
    def answer_question(self) -> AnswerQuestion:
        return AnswerQuestion(
            store=self.store,
            embedder=self.embedder,
            llm=self.llm,
            settings=self.settings,
        )

    @cached_property
    def generate_mindmap(self) -> GenerateMindmap:
        return GenerateMindmap(
            store=self.store,
            embedder=self.embedder,
            llm=self.llm,
            settings=self.settings,
        )
