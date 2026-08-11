# app/usecases/ingest_document.py
"""Usecase: nạp một file PDF vào vector store."""
from dataclasses import dataclass

from app.domain.chunking import chunk_pages
from app.domain.errors import InvalidDocumentError
from app.domain.models import DocumentRef
from app.domain.ports import DocumentLoader, EmbeddingProvider, VectorStore
from app.infra.logging import get_logger
from app.infra.settings import Settings

logger = get_logger("ingest")


@dataclass(frozen=True)
class IngestResult:
    """Kết quả nạp tài liệu."""

    ref: DocumentRef
    chunk_count: int
    page_count: int


class IngestDocument:
    """Đọc PDF -> cắt chunk -> nhúng vector -> lưu vào store."""

    def __init__(
        self,
        *,
        loader: DocumentLoader,
        store: VectorStore,
        embedder: EmbeddingProvider,
        settings: Settings,
    ) -> None:
        self._loader = loader
        self._store = store
        self._embedder = embedder
        self._settings = settings

    def execute(self, *, filename: str, data: bytes, owner_id: str) -> IngestResult:
        """Nạp tài liệu và trả về tham chiếu tới nó.

        `owner_id` giới hạn phạm vi tác động: chỉ tài liệu cũ của chính phiên
        này bị dọn đi, tài liệu của phiên khác không bị ảnh hưởng.
        """
        pages = self._loader.load_pages(data)

        chunks = chunk_pages(
            pages,
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )
        if not chunks:
            raise InvalidDocumentError("Không cắt được đoạn văn bản nào từ tài liệu.")

        logger.info("Tài liệu '%s': %d trang -> %d chunk", filename, len(pages), len(chunks))

        embeddings = self._embedder.embed_documents([chunk.text for chunk in chunks])

        ref = self._store.create_document(
            display_name=filename,
            owner_id=owner_id,
            embedding_model=self._embedder.model_name,
            chunks=chunks,
            embeddings=embeddings,
        )
        return IngestResult(ref=ref, chunk_count=len(chunks), page_count=len(pages))
