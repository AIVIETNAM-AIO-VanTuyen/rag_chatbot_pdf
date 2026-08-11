# app/domain/ports.py
"""Các interface (port) mà tầng adapter phải hiện thực.

Usecase chỉ phụ thuộc vào các Protocol dưới đây chứ không gọi thẳng SDK của
nhà cung cấp. Hai lợi ích: test thay được provider thật bằng đối tượng giả (nên
toàn bộ test chạy offline), và muốn đổi/thêm nhà cung cấp thì chỉ viết thêm một
adapter mà không đụng tới logic nghiệp vụ.
"""
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.domain.models import ChatTurn, Chunk, DocumentRef, RetrievedChunk


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Chuyển văn bản thành vector."""

    # Định danh model, được ghi lại cùng tài liệu để phát hiện lệch số chiều.
    model_name: str

    def is_available(self) -> bool:
        """Provider có sẵn sàng nhận request không."""
        ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Nhúng các đoạn văn bản của tài liệu (bên được lưu vào index)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Nhúng câu truy vấn của người dùng (bên đi tìm kiếm)."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Sinh văn bản từ hội thoại."""

    model_name: str

    def is_available(self) -> bool:
        """Provider có sẵn sàng nhận request không."""
        ...

    def complete(
        self,
        messages: Sequence[ChatTurn],
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        """Sinh câu trả lời cho chuỗi hội thoại `messages`."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Lưu trữ và truy vấn vector."""

    def create_document(
        self,
        *,
        display_name: str,
        owner_id: str,
        embedding_model: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
    ) -> DocumentRef:
        """Tạo một tài liệu mới trong store và trả về tham chiếu tới nó."""
        ...

    def search(
        self,
        ref: DocumentRef,
        query_embedding: Sequence[float],
        *,
        k: int,
    ) -> list[RetrievedChunk]:
        """Tìm `k` đoạn gần nhất với vector truy vấn trong tài liệu `ref`."""
        ...

    def list_documents(self, owner_id: str) -> list[DocumentRef]:
        """Liệt kê tài liệu THUỘC VỀ `owner_id`, không đụng tới người khác."""
        ...

    def delete_documents(self, owner_id: str) -> int:
        """Xoá toàn bộ tài liệu của `owner_id`. Trả về số tài liệu đã xoá."""
        ...


@runtime_checkable
class DocumentLoader(Protocol):
    """Đọc file tải lên và trích xuất văn bản theo từng trang."""

    def load_pages(self, data: bytes) -> list[str]:
        """Trả về danh sách văn bản, mỗi phần tử là nội dung của một trang."""
        ...
