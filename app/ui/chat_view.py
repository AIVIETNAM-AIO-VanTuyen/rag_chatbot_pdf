# app/ui/chat_view.py
import streamlit as st

from app.ui.mindmap_dot import render_radial, render_tree, summarize_mindmap
from app.ui.sidebar import show_sidebar
from app.ui.state import chat_turns, current_document, describe_error, get_container

_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

/* Cải thiện sidebar */
[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Hiệu ứng bo góc và đổ bóng nhẹ cho nút */
.stButton>button {
    border-radius: 12px;
    font-weight: 600;
    transition: all 0.3s ease;
}

/* Làm đẹp khối thông tin và trợ lý */
.doc-badge {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
    border: 1px solid rgba(99, 102, 241, 0.2);
    color: #c7d2fe;
    padding: 10px 16px;
    border-radius: 12px;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 1rem;
}
</style>
"""

_ANSWER_SPINNER = "Đang trích xuất dữ liệu và suy nghĩ..."
_MINDMAP_SPINNER = "Đang phân tích nội dung tài liệu và lập sơ đồ tư duy..."

_STYLE_RADIAL = "🧠 Tỏa tròn từ tâm"
_STYLE_HORIZONTAL = "📊 Nhánh ngang"
_STYLE_VERTICAL = "📈 Nhánh dọc"


def _is_busy() -> bool:
    """Đang có việc chạy dở hay không.

    Mọi nút gây rerun đều phải khoá khi True: một lượt rerun giữa chừng sẽ huỷ
    luôn công việc đang chạy.
    """
    return st.session_state.pending_question is not None or st.session_state.pending_mindmap


def _render_document_header(document, *, is_busy: bool) -> None:
    """Badge tên tài liệu, kèm nút xuất sơ đồ tư duy ngay bên cạnh."""
    badge_column, action_column = st.columns([3, 1], vertical_alignment="center")

    with badge_column:
        st.markdown(
            f"<div class='doc-badge'>🤖 Đang hỏi đáp với tài liệu: {document.display_name}</div>",
            unsafe_allow_html=True,
        )

    with action_column:
        if st.button(
            "📊 Xuất sơ đồ tư duy",
            use_container_width=True,
            type="primary",
            disabled=is_busy,
        ):
            st.session_state.pending_mindmap = True
            st.rerun()


def _render_mindmap(message: dict, *, index: int) -> None:
    """Vẽ sơ đồ tư duy ngay trong khung hội thoại."""
    data = message["data"]
    fallback_title = message.get("document_name", "Tài liệu")

    style = st.radio(
        "Kiểu hiển thị:",
        [_STYLE_RADIAL, _STYLE_HORIZONTAL, _STYLE_VERTICAL],
        horizontal=True,
        # Mỗi sơ đồ trong hội thoại giữ lựa chọn riêng, nên key phải theo vị trí.
        key=f"mindmap_style_{index}",
    )

    if style == _STYLE_RADIAL:
        dot_code = render_radial(data, fallback_title=fallback_title)
    else:
        rankdir = "LR" if style == _STYLE_HORIZONTAL else "TB"
        dot_code = render_tree(data, fallback_title=fallback_title, rankdir=rankdir)

    try:
        st.graphviz_chart(dot_code)
    except Exception as error:  # noqa: BLE001 - lỗi cú pháp DOT cần hiện ra để sửa
        st.error(f"Có lỗi khi vẽ sơ đồ bằng Graphviz: {error}")
        st.code(dot_code, language="dot")


def _render_history() -> None:
    """Vẽ lại toàn bộ hội thoại đã hoàn tất."""
    for index, message in enumerate(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            if message.get("kind") == "mindmap":
                _render_mindmap(message, index=index)
                continue

            st.write(message["content"])
            # Số trang được lưu cùng tin nhắn nên phần trích dẫn không biến mất
            # sau mỗi lần Streamlit rerun.
            pages = message.get("pages")
            if pages:
                st.caption(f"📄 Nguồn: trang {', '.join(str(page) for page in pages)}")


def _build_answer_message(question: str) -> dict:
    """Gọi usecase RAG và dựng tin nhắn trả lời."""
    # `history` là các lượt TRƯỚC câu hỏi này. Câu hỏi hiện tại đã được thêm
    # vào chat_history ở lần chạy trước nên phải bỏ phần tử cuối ra.
    history = chat_turns()[:-1]

    with st.chat_message("assistant"), st.spinner(_ANSWER_SPINNER):
        try:
            answer = get_container().answer_question.execute(
                ref=current_document(),
                question=question,
                history=history,
            )
        except Exception as error:  # noqa: BLE001 - hiển thị lỗi cho người dùng
            return {"role": "assistant", "content": describe_error(error, context="Trả lời câu hỏi")}

    return {"role": "assistant", "content": answer.text, "pages": answer.pages}


def _build_mindmap_message() -> dict:
    """Sinh sơ đồ tư duy và dựng tin nhắn chứa nó."""
    document = current_document()

    with st.chat_message("assistant"), st.spinner(_MINDMAP_SPINNER):
        try:
            data = get_container().generate_mindmap.execute(document)
        except Exception as error:  # noqa: BLE001 - hiển thị lỗi cho người dùng
            return {
                "role": "assistant",
                "content": describe_error(error, context="Tạo sơ đồ tư duy"),
            }

    return {
        "role": "assistant",
        "kind": "mindmap",
        "data": data,
        "document_name": document.display_name,
        # Bản chữ của sơ đồ: người dùng nhìn hình, còn LLM đọc phần này khi
        # được hỏi tiếp "sơ đồ trên nói về vấn đề gì".
        "content": summarize_mindmap(data, fallback_title=document.display_name),
    }


def _process_pending_work() -> None:
    """Chạy việc đang chờ (trả lời hoặc vẽ sơ đồ) rồi ghi kết quả vào lịch sử."""
    question = st.session_state.pending_question

    try:
        message = _build_answer_message(question) if question else _build_mindmap_message()
    finally:
        # Xoá cờ bận trong `finally`: nếu một lỗi ngoài dự kiến làm hàm dựng tin
        # nhắn văng ra sớm, cờ vẫn phải được gỡ — không thì ô nhập kẹt ở trạng
        # thái khoá và người dùng không còn cách nào thoát ra ngoài F5.
        st.session_state.pending_question = None
        st.session_state.pending_mindmap = False

    st.session_state.chat_history.append(message)
    st.rerun()


def show_chat_view():
    """Hiển thị giao diện chính ứng dụng RAG Chatbot."""
    st.markdown(_STYLES, unsafe_allow_html=True)

    show_sidebar()

    st.markdown("<h1 style='margin-bottom: 0px;'>📚 Thư Viện Tài Liệu RAG AI</h1>", unsafe_allow_html=True)

    document = current_document()
    is_busy = _is_busy()

    if document is not None:
        _render_document_header(document, is_busy=is_busy)
    else:
        st.markdown(
            "<div style='color: #64748b; font-size: 0.95rem; margin-bottom: 1.5rem;'>Vui lòng nạp tài liệu để bắt đầu trò chuyện.</div>",
            unsafe_allow_html=True
        )

    _render_history()

    if document is None:
        st.info("Vui lòng nạp tài liệu PDF từ thanh bên để bắt đầu hỏi đáp.")
        st.chat_input("Nhập câu hỏi...", disabled=True)
        return

    question = st.chat_input(
        "Đang xử lý, vui lòng đợi..." if is_busy else "Nhập câu hỏi của bạn về nội dung tài liệu...",
        disabled=is_busy,
    )

    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        st.session_state.pending_question = question
        # Rerun để ô nhập kịp chuyển sang trạng thái khoá TRƯỚC khi gọi API.
        st.rerun()

    if is_busy:
        _process_pending_work()
