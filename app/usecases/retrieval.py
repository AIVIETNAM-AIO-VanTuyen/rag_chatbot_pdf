# app/usecases/retrieval.py
"""Phần truy hồi dùng chung giữa các usecase."""
from collections.abc import Sequence

from app.domain.errors import EmbeddingModelMismatchError
from app.domain.models import DocumentRef, RetrievedChunk
from app.domain.ports import EmbeddingProvider


def format_context(chunks: Sequence[RetrievedChunk]) -> str:
    """Ghép các đoạn truy hồi thành khối ngữ cảnh, có đánh dấu số trang.

    Số trang được gắn ở ĐÂY, lúc dựng prompt — chứ không nhúng sẵn vào text
    trước khi embed như bản cũ. Nhờ vậy vector chỉ mang ngữ nghĩa nội dung,
    còn LLM vẫn biết thông tin đến từ trang nào.
    """
    blocks: list[str] = []
    for chunk in chunks:
        header = f"[Trang {chunk.page}]" if chunk.page else "[Không rõ trang]"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n".join(blocks)


def ensure_model_matches(ref: DocumentRef, embedder: EmbeddingProvider) -> None:
    """Chặn truy vấn tài liệu đã nhúng bằng model khác model đang cấu hình.

    Mỗi model embedding sinh vector với số chiều và không gian ngữ nghĩa riêng.
    Đem vector của model này đi so khớp với index của model kia thì kết quả vô
    nghĩa, hoặc ChromaDB báo lỗi lệch số chiều. Thà báo sớm và rõ.
    """
    if ref.embedding_model == embedder.model_name:
        return
    raise EmbeddingModelMismatchError(
        f"Tài liệu '{ref.display_name}' được nhúng bằng model "
        f"'{ref.embedding_model}', nhưng hiện đang cấu hình '{embedder.model_name}'.",
        hint="Hãy nạp lại tài liệu, hoặc đổi GEMINI_EMBED_MODEL về giá trị cũ.",
    )
