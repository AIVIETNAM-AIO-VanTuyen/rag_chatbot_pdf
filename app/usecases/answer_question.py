# app/usecases/answer_question.py
"""Usecase: trả lời câu hỏi dựa trên tài liệu đã nạp (luồng RAG)."""
from collections.abc import Sequence

from app.domain.models import Answer, ChatTurn, DocumentRef
from app.domain.ports import EmbeddingProvider, LLMProvider, VectorStore
from app.infra.logging import get_logger
from app.infra.settings import Settings
from app.usecases.prompts import ANSWER_SYSTEM_PROMPT, ANSWER_USER_TEMPLATE
from app.usecases.retrieval import ensure_model_matches, format_context

logger = get_logger("answer")


class AnswerQuestion:
    """Nhúng câu hỏi -> truy hồi ngữ cảnh -> sinh câu trả lời."""

    def __init__(
        self,
        *,
        store: VectorStore,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        settings: Settings,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._llm = llm
        self._settings = settings

    def execute(
        self,
        *,
        ref: DocumentRef,
        question: str,
        history: Sequence[ChatTurn] = (),
    ) -> Answer:
        """Trả lời `question` trong phạm vi tài liệu `ref`.

        `history` là các lượt hội thoại TRƯỚC ĐÓ, KHÔNG bao gồm `question`.
        Bản cũ hoàn toàn không gửi lịch sử cho LLM, nên mọi câu hỏi nối tiếp
        kiểu "giải thích rõ hơn đi" hay "cái đó là gì" đều mất ngữ cảnh.
        """
        ensure_model_matches(ref, self._embedder)

        query_vector = self._embedder.embed_query(question)
        chunks = self._store.search(ref, query_vector, k=self._settings.retrieval_top_k)

        if not chunks:
            logger.warning("Không truy hồi được đoạn nào cho câu hỏi: %r", question)
            return Answer(
                text="Tôi không tìm thấy thông tin liên quan trong tài liệu này.",
                sources=[],
            )

        messages = self._build_messages(history, question, format_context(chunks))
        text = self._llm.complete(
            messages,
            system=ANSWER_SYSTEM_PROMPT,
            temperature=self._settings.answer_temperature,
        )
        return Answer(text=text.strip(), sources=chunks)

    def _build_messages(
        self,
        history: Sequence[ChatTurn],
        question: str,
        context: str,
    ) -> list[ChatTurn]:
        """Dựng chuỗi tin nhắn: N lượt gần nhất + câu hỏi hiện tại kèm ngữ cảnh."""
        turns = self._settings.history_turns
        recent = list(history)[-turns:] if turns else []
        messages = list(recent)
        messages.append(
            ChatTurn(
                role="user",
                content=ANSWER_USER_TEMPLATE.format(context=context, question=question),
            )
        )
        return messages
