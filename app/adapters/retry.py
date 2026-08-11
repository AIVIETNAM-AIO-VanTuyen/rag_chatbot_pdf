# app/adapters/retry.py
"""Cơ chế thử lại với thời gian giãn cách tăng dần (exponential backoff).

Bản cũ lặp lại logic này bốn lần trong `rag.py` (hai lần cho embed, hai lần cho
generate). Giờ gom về một chỗ để mọi adapter dùng chung.
"""
import time
from collections.abc import Callable
from typing import TypeVar

from app.domain.errors import ProviderError
from app.infra.logging import get_logger

T = TypeVar("T")
logger = get_logger("retry")


def with_retry(
    operation: Callable[[], T],
    *,
    attempts: int,
    base_delay: float,
    description: str,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Chạy `operation`, thử lại tối đa `attempts` lần khi có lỗi.

    Lần chờ thứ i kéo dài `base_delay * 2**i` giây. Hết lượt vẫn lỗi thì ném
    `ProviderError` với nguyên nhân gốc đính kèm (`raise ... from`).
    """
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            return operation()
        except Exception as error:  # noqa: BLE001 - gói lại thành lỗi nghiệp vụ
            last_error = error
            if attempt == attempts - 1:
                break
            delay = base_delay * (2**attempt)
            logger.warning(
                "%s thất bại (lần %d/%d): %s. Thử lại sau %.1fs",
                description,
                attempt + 1,
                attempts,
                error,
                delay,
            )
            sleep(delay)

    logger.error("%s thất bại sau %d lần thử: %s", description, attempts, last_error)
    raise ProviderError(
        f"{description} thất bại sau {attempts} lần thử.",
        hint="Vui lòng thử lại sau ít phút.",
    ) from last_error
