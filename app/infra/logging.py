# app/infra/logging.py
"""Thiết lập logging cho toàn ứng dụng.

Thay cho các lệnh `print()` rải rác trong code cũ — đáng chú ý là bản cũ dump
nội dung ĐẦY ĐỦ của từng chunk ra stdout mỗi lần nạp tài liệu.
"""
import logging
import sys

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO") -> None:
    """Cấu hình logger gốc. Gọi nhiều lần cũng chỉ có tác dụng một lần."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger("app")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False

    # Các thư viện phía dưới rất ồn ở mức INFO.
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Lấy logger nằm dưới namespace `app`."""
    return logging.getLogger(f"app.{name}")
