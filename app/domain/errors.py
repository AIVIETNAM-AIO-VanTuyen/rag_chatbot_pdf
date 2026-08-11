# app/domain/errors.py
"""Các lỗi nghiệp vụ của ứng dụng.

Dùng exception có kiểu thay vì `ValueError` chung chung để UI biết cách hiển thị
thông báo phù hợp, và để không còn chỗ nào phải `except Exception: pass`.
"""


class AppError(Exception):
    """Lỗi gốc của ứng dụng. Mọi lỗi nghiệp vụ đều kế thừa từ đây."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message} {self.hint}"
        return self.message


class ProviderUnavailableError(AppError):
    """Chưa cấu hình được nhà cung cấp mô hình nên không thể phục vụ."""


class EmbeddingModelMismatchError(AppError):
    """Tài liệu được nhúng bằng model khác với model đang cấu hình."""


class ProviderError(AppError):
    """Nhà cung cấp mô hình trả về lỗi sau khi đã thử lại hết số lần cho phép."""


class DocumentNotFoundError(AppError):
    """Tài liệu được tham chiếu không còn tồn tại trong vector store."""


class InvalidDocumentError(AppError):
    """File tải lên không hợp lệ (rỗng, quá lớn, hỏng, không đọc được chữ)."""


class MindmapParseError(AppError):
    """Không thể đọc được JSON sơ đồ tư duy mà LLM trả về."""
