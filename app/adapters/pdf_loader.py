# app/adapters/pdf_loader.py
"""Adapter pypdf cho port `DocumentLoader`."""
import io

import pypdf

from app.domain.errors import InvalidDocumentError
from app.infra.logging import get_logger
from app.infra.settings import Settings

logger = get_logger("pdf")


class PyPdfLoader:
    """Đọc PDF từ bytes và trích xuất văn bản theo từng trang.

    Đọc thẳng từ bộ nhớ qua `io.BytesIO` thay vì ghi ra file tạm rồi xoá như
    bản cũ — bớt được I/O đĩa và không còn nguy cơ để lại file rác.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def load_pages(self, data: bytes) -> list[str]:
        """Trả về danh sách văn bản theo trang. Trang không có chữ trả về chuỗi rỗng."""
        if not data:
            raise InvalidDocumentError("File tải lên rỗng.")

        limit = self._settings.max_pdf_bytes
        if len(data) > limit:
            raise InvalidDocumentError(
                f"File nặng {len(data) / 1024 / 1024:.1f}MB, vượt giới hạn "
                f"{self._settings.max_pdf_mb:.0f}MB.",
                hint="Hãy tách nhỏ tài liệu hoặc tăng MAX_PDF_MB trong .env.",
            )

        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
            page_count = len(reader.pages)
        except Exception as error:  # noqa: BLE001
            logger.error("Không đọc được file PDF: %s", error)
            raise InvalidDocumentError(
                "Không đọc được file PDF (file hỏng hoặc đang được mã hoá).",
            ) from error

        if page_count > self._settings.max_pdf_pages:
            raise InvalidDocumentError(
                f"Tài liệu có {page_count} trang, vượt giới hạn "
                f"{self._settings.max_pdf_pages} trang.",
                hint="Hãy tách nhỏ tài liệu hoặc tăng MAX_PDF_PAGES trong .env.",
            )

        pages: list[str] = []
        for page_index, page in enumerate(reader.pages):
            try:
                pages.append(page.extract_text() or "")
            except Exception as error:  # noqa: BLE001 - hỏng một trang không nên chặn cả file
                logger.warning("Bỏ qua trang %d vì lỗi trích xuất: %s", page_index + 1, error)
                pages.append("")

        extracted = sum(1 for text in pages if text.strip())
        logger.info("Đã đọc %d/%d trang có nội dung chữ", extracted, page_count)
        if extracted == 0:
            raise InvalidDocumentError(
                "Không trích xuất được chữ nào từ tài liệu.",
                hint="Có thể đây là PDF scan ảnh — cần OCR, hiện chưa được hỗ trợ.",
            )
        return pages
