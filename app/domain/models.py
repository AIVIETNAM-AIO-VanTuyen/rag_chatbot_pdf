# app/domain/models.py
"""Các model dữ liệu dùng chung giữa các tầng."""
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class Chunk:
    """Một đoạn văn bản đã cắt từ tài liệu, kèm metadata nguồn gốc.

    Số trang nằm ở đây (metadata) chứ KHÔNG nhúng vào `text`, để không làm
    nhiễu vector embedding và để có thể lọc/trích dẫn theo trang về sau.
    """

    text: str
    page: int
    index: int


@dataclass(frozen=True)
class RetrievedChunk:
    """Một đoạn văn bản lấy được từ vector store khi truy vấn."""

    text: str
    page: int
    distance: float | None = None


@dataclass(frozen=True)
class ChatTurn:
    """Một lượt hội thoại."""

    role: Role
    content: str


@dataclass(frozen=True)
class DocumentRef:
    """Tham chiếu tới một tài liệu đã index.

    Đây là dữ liệu thuần (picklable), KHÔNG phải handle sống của ChromaDB.
    UI giữ ref này trong session_state; vector store tra cứu lại collection
    theo `collection_name` mỗi lần dùng. Nhờ vậy ref không bao giờ bị "chết"
    khi collection phía dưới thay đổi.
    """

    collection_name: str
    display_name: str
    # Model đã dùng để nhúng tài liệu này. Truy vấn phải dùng đúng model đó,
    # nếu không số chiều vector sẽ lệch và kết quả truy hồi trở nên vô nghĩa.
    embedding_model: str
    owner_id: str
    chunk_count: int = 0


@dataclass
class Answer:
    """Kết quả trả lời của luồng RAG."""

    text: str
    sources: list[RetrievedChunk] = field(default_factory=list)

    @property
    def pages(self) -> list[int]:
        """Danh sách số trang đã dùng làm ngữ cảnh, không trùng lặp, đã sắp xếp."""
        return sorted({c.page for c in self.sources if c.page > 0})
