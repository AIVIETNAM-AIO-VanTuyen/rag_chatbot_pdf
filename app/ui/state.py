# app/ui/state.py
"""Cầu nối giữa Streamlit và phần lõi: container, session state, xử lý lỗi."""
import uuid
from collections.abc import Sequence

import streamlit as st

from app.domain.errors import AppError
from app.domain.models import ChatTurn, DocumentRef
from app.infra.container import Container
from app.infra.logging import get_logger

logger = get_logger("ui")

# Các khoá session_state và giá trị mặc định của chúng.
_DEFAULTS: dict[str, object] = {
    "authenticated": False,
    "username": "",
    "owner_id": "",
    "document": None,
    "chat_history": [],
    # Câu hỏi đang chờ trợ lý trả lời. Khác None nghĩa là đang bận.
    "pending_question": None,
    # True khi đang sinh sơ đồ tư duy.
    "pending_mindmap": False,
}


@st.cache_resource(show_spinner=False)
def get_container() -> Container:
    """Container dùng chung cho cả tiến trình.

    `cache_resource` giữ nguyên một instance qua mọi lần rerun của Streamlit —
    bản cũ tạo lại client Gemini ở mỗi lần import module.
    """
    return Container()


def init_session_state() -> None:
    """Khởi tạo các khoá session_state còn thiếu."""
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = list(value) if isinstance(value, list) else value

    # Mỗi phiên trình duyệt có một định danh riêng, dùng để cô lập dữ liệu
    # trong vector store giữa những người dùng đang mở app cùng lúc.
    if not st.session_state.owner_id:
        st.session_state.owner_id = uuid.uuid4().hex


def reset_document_state() -> None:
    """Xoá trạng thái gắn với tài liệu đang mở."""
    st.session_state.document = None
    st.session_state.chat_history = []
    st.session_state.pending_question = None
    st.session_state.pending_mindmap = False


def sign_in(username: str) -> None:
    """Đánh dấu phiên đã đăng nhập."""
    st.session_state.authenticated = True
    st.session_state.username = username


def sign_out() -> None:
    """Đăng xuất và dọn sạch dữ liệu của phiên, kể cả trong vector store."""
    owner_id = st.session_state.get("owner_id")
    if owner_id:
        try:
            get_container().store.delete_documents(owner_id)
        except Exception:  # noqa: BLE001 - đăng xuất không được phép thất bại
            logger.exception("Không dọn được tài liệu khi đăng xuất")

    reset_document_state()
    st.session_state.authenticated = False
    st.session_state.username = ""
    # Cấp định danh mới để phiên đăng nhập kế tiếp không kế thừa dữ liệu cũ.
    st.session_state.owner_id = uuid.uuid4().hex


def current_document() -> DocumentRef | None:
    """Tài liệu đang được chọn trong phiên này."""
    return st.session_state.get("document")


def chat_turns() -> list[ChatTurn]:
    """Lịch sử hội thoại dưới dạng model domain, để truyền thẳng cho usecase.

    Bỏ qua tin nhắn không có phần chữ. Không phải mọi thứ trong hội thoại đều
    là văn bản — ví dụ tin nhắn sơ đồ tư duy — nên phải dùng `.get()` thay vì
    truy cập thẳng khoá `content`.
    """
    history: Sequence[dict[str, str]] = st.session_state.get("chat_history", [])
    return [
        ChatTurn(role=item["role"], content=item["content"])
        for item in history
        if item.get("content")
    ]


def describe_error(error: Exception, *, context: str) -> str:
    """Ghi log đầy đủ cho lập trình viên và trả về câu thông báo cho người dùng.

    Lỗi nghiệp vụ (`AppError`) có thông điệp tiếng Việt rõ ràng nên hiện thẳng;
    lỗi ngoài dự kiến chỉ hiện thông báo chung, chi tiết đẩy vào log.
    """
    if isinstance(error, AppError):
        logger.warning("%s: %s", context, error)
        return f"❌ {error}"

    logger.exception("%s: lỗi ngoài dự kiến", context)
    return f"❌ {context} không thành công. Vui lòng thử lại sau."


def show_error(error: Exception, *, context: str) -> None:
    """Hiển thị lỗi ngay tại chỗ."""
    st.error(describe_error(error, context=context))
