# app/adapters/gemini_provider.py
"""Adapter Google Gemini cho hai port `LLMProvider` và `EmbeddingProvider`."""
import time
from collections.abc import Sequence
from functools import cached_property

from google import genai
from google.genai import types

from app.adapters.retry import with_retry
from app.domain.errors import ProviderUnavailableError
from app.domain.models import ChatTurn
from app.infra.logging import get_logger
from app.infra.settings import Settings

logger = get_logger("gemini")

NO_KEY_HINT = (
    "Hãy thêm GEMINI_API_KEY vào file .env rồi khởi động lại ứng dụng "
    "(lấy key tại https://aistudio.google.com/)."
)

# Gemini dùng nhãn "model" cho lượt của trợ lý, khác với quy ước "assistant".
_ROLE_MAP = {"user": "user", "assistant": "model"}


class _GeminiClientMixin:
    """Phần khởi tạo client dùng chung cho cả LLM và embedding."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @cached_property
    def _client(self) -> genai.Client:
        """Tạo client Gemini, ném lỗi rõ ràng nếu thiếu hoặc sai API key.

        Bản cũ nuốt lỗi bằng `except Exception: pass` rồi để client là None,
        nên mãi tới lúc người dùng hỏi mới báo lỗi mà không nói được lý do.
        """
        if not self._settings.gemini_api_key:
            raise ProviderUnavailableError("Chưa cấu hình GEMINI_API_KEY.", hint=NO_KEY_HINT)
        try:
            return genai.Client(api_key=self._settings.gemini_api_key)
        except Exception as error:  # noqa: BLE001
            logger.error("Không khởi tạo được Gemini client: %s", error)
            raise ProviderUnavailableError(
                "Không khởi tạo được Gemini client.", hint=NO_KEY_HINT
            ) from error

    def is_available(self) -> bool:
        return bool(self._settings.gemini_api_key)

    def _require_available(self) -> None:
        if not self.is_available():
            raise ProviderUnavailableError("Chưa cấu hình GEMINI_API_KEY.", hint=NO_KEY_HINT)


class GeminiEmbeddingProvider(_GeminiClientMixin):
    """Nhúng văn bản bằng Gemini Embedding API, có chia batch và backoff."""

    @property
    def model_name(self) -> str:
        return self._settings.gemini_embed_model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        self._require_available()

        batch_size = self._settings.gemini_embed_batch_size
        vectors: list[list[float]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        logger.info("Nhúng %d đoạn văn bản bằng Gemini (%d batch)", len(texts), total_batches)

        for batch_index, start in enumerate(range(0, len(texts), batch_size)):
            batch = list(texts[start : start + batch_size])
            vectors.extend(self._embed_batch(batch))
            # Nghỉ giữa các batch để tránh dính rate limit 429.
            if batch_index < total_batches - 1 and self._settings.gemini_batch_pause_seconds:
                time.sleep(self._settings.gemini_batch_pause_seconds)

        return vectors

    def embed_query(self, text: str) -> list[float]:
        self._require_available()
        return self._embed_batch([text])[0]

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        def call() -> list[list[float]]:
            response = self._client.models.embed_content(
                model=self._settings.gemini_embed_model,
                contents=batch,
            )
            embeddings = getattr(response, "embeddings", None)
            if embeddings is None:
                embeddings = response.get("embeddings", [])

            vectors: list[list[float]] = []
            for item in embeddings:
                values = getattr(item, "values", None)
                if values is None and isinstance(item, dict):
                    values = item.get("values", [])
                vectors.append(list(values or []))
            return vectors

        return with_retry(
            call,
            attempts=self._settings.embed_max_attempts,
            base_delay=self._settings.retry_base_delay_seconds,
            description=f"Nhúng văn bản bằng Gemini ({self._settings.gemini_embed_model})",
        )


class GeminiLLMProvider(_GeminiClientMixin):
    """Sinh câu trả lời bằng Gemini."""

    @property
    def model_name(self) -> str:
        return self._settings.gemini_llm_model

    def complete(
        self,
        messages: Sequence[ChatTurn],
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        self._require_available()

        contents = [
            types.Content(
                role=_ROLE_MAP.get(turn.role, "user"),
                parts=[types.Part(text=turn.content)],
            )
            for turn in messages
        ]
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system or None,
        )

        def call() -> str:
            response = self._client.models.generate_content(
                model=self._settings.gemini_llm_model,
                contents=contents,
                config=config,
            )
            return extract_text(response)

        logger.info("Gọi Gemini %s với %d tin nhắn", self._settings.gemini_llm_model, len(contents))
        return with_retry(
            call,
            attempts=self._settings.llm_max_attempts,
            base_delay=self._settings.retry_base_delay_seconds,
            description=f"Sinh câu trả lời bằng Gemini ({self._settings.gemini_llm_model})",
        )


def extract_text(response: object) -> str:
    """Lấy phần văn bản từ response của Gemini.

    Đi qua `candidates[0].content.parts` trước để tránh cảnh báo khi response
    có phần không phải text (ví dụ `thought_signature`), rồi mới lùi về `.text`.
    """
    try:
        parts = response.candidates[0].content.parts  # type: ignore[attr-defined]
        texts = [part.text for part in parts if getattr(part, "text", None)]
        if texts:
            return "".join(texts)
    except (AttributeError, IndexError, TypeError):
        pass

    text = getattr(response, "text", None)
    return text if text else str(response)
