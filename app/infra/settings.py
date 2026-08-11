# app/infra/settings.py
"""Cấu hình ứng dụng, đọc từ biến môi trường / file .env và có kiểm tra hợp lệ.

Thay cho `app/config.py` cũ (chỉ là các hằng số trần, không validate, và có
`CHROMA_DB_DIR` khai báo rồi không ai dùng). Mọi tham số giờ đều chỉnh được qua
.env mà không cần sửa code.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toàn bộ tham số vận hành của ứng dụng."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Google Gemini ---------------------------------------------------
    gemini_api_key: str | None = None
    gemini_llm_model: str = "gemini-3.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"
    gemini_embed_batch_size: int = Field(default=20, ge=1, le=100)
    gemini_batch_pause_seconds: float = Field(default=1.0, ge=0)

    # --- Vector store -----------------------------------------------------
    # None = chạy in-memory (mất khi tắt app), giữ đúng hành vi hiện tại.
    # Đặt CHROMA_PERSIST_DIR=./data/chroma_db để lưu xuống ổ cứng.
    chroma_persist_dir: Path | None = None

    # --- Xử lý tài liệu ---------------------------------------------------
    chunk_size: int = Field(default=1000, ge=100)
    chunk_overlap: int = Field(default=200, ge=0)
    max_pdf_mb: float = Field(default=25.0, gt=0)
    max_pdf_pages: int = Field(default=500, ge=1)

    # --- Truy hồi & sinh câu trả lời ---------------------------------------
    retrieval_top_k: int = Field(default=4, ge=1, le=50)
    mindmap_top_k: int = Field(default=6, ge=1, le=50)
    # Số lượt hội thoại gần nhất được gửi kèm cho LLM.
    history_turns: int = Field(default=6, ge=0, le=50)
    answer_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    mindmap_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # --- Thử lại ------------------------------------------------------------
    llm_max_attempts: int = Field(default=3, ge=1, le=10)
    embed_max_attempts: int = Field(default=5, ge=1, le=10)
    retry_base_delay_seconds: float = Field(default=1.0, ge=0)

    # --- Đăng nhập ----------------------------------------------------------
    # Tạm thời vẫn là tài khoản demo, nhưng đã rút khỏi source ra .env.
    # Xác thực thật (SQLite + bcrypt) thuộc Phase 3.
    auth_username: str = "admin"
    auth_password: str = "admin123"

    # --- Logging ------------------------------------------------------------
    log_level: str = "INFO"

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_must_fit(cls, value: int, info: ValidationInfo) -> int:
        chunk_size = info.data.get("chunk_size")
        if chunk_size is not None and value >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({value}) phải nhỏ hơn chunk_size ({chunk_size})"
            )
        return value

    @field_validator("gemini_api_key")
    @classmethod
    def _blank_key_is_none(cls, value: str | None) -> str | None:
        """Coi chuỗi rỗng / placeholder trong .env mẫu là chưa cấu hình."""
        if value is None:
            return None
        value = value.strip()
        if not value or value.startswith("your_"):
            return None
        return value

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in allowed:
            raise ValueError(f"log_level phải thuộc {sorted(allowed)}, nhận được {value!r}")
        return level

    @property
    def has_gemini(self) -> bool:
        """Đã cấu hình đủ để gọi Gemini hay chưa."""
        return bool(self.gemini_api_key)

    @property
    def max_pdf_bytes(self) -> int:
        """Giới hạn dung lượng file tải lên, quy ra byte."""
        return int(self.max_pdf_mb * 1024 * 1024)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Trả về cấu hình dùng chung (đọc .env đúng một lần cho cả tiến trình)."""
    return Settings()
