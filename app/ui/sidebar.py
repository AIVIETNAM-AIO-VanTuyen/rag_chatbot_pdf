# app/ui/sidebar.py
import streamlit as st

from app.ui.state import (
    get_container,
    reset_document_state,
    show_error,
    sign_out,
)


def _provider_badge() -> None:
    """Cho biết đã cấu hình xong chưa, thay vì để người dùng đoán."""
    container = get_container()
    if container.is_ready:
        st.caption(f"⚡ Engine: Gemini · {container.settings.gemini_llm_model}")
    else:
        st.warning("Chưa cấu hình GEMINI_API_KEY trong file .env — chưa thể nạp tài liệu.")


def show_sidebar():
    """Hiển thị thanh Sidebar điều khiển bên trái."""
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px;">
                <span style="font-size: 1.1rem; color: #a5b4fc; font-weight: 600;">👤 Admin:</span>
                <span style="font-size: 1.1rem; color: #ffffff; font-weight: 700;">{st.session_state.username}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            sign_out()
            st.rerun()

        st.write("---")
        st.subheader("📥 Nạp thêm tài liệu mới")
        _provider_badge()
        uploaded = st.file_uploader("Chọn file PDF mới", type="pdf")

        if uploaded and st.button("🚀 Xử lý và Thêm vào thư viện", use_container_width=True, type="primary"):
            with st.spinner("Đang phân tích và index dữ liệu..."):
                try:
                    result = get_container().ingest_document.execute(
                        filename=uploaded.name,
                        data=uploaded.getvalue(),
                        owner_id=st.session_state.owner_id,
                    )
                except Exception as error:  # noqa: BLE001 - hiển thị lỗi cho người dùng
                    show_error(error, context="Xử lý file PDF")
                else:
                    reset_document_state()
                    st.session_state.document = result.ref
                    st.success(
                        f"Đã nạp thành công: {uploaded.name} "
                        f"({result.page_count} trang, {result.chunk_count} chunks)"
                    )
                    st.rerun()

        # Nút "Xuất sơ đồ tư duy" nằm ngay trong khu vực trò chuyện
        # (app/ui/chat_view.py) chứ không còn ở đây.

        st.write("---")
        st.subheader("⚙️ Quản lý cuộc trò chuyện")
        if st.button("🧹 Xóa lịch sử chat", use_container_width=True):
            st.session_state.chat_history = []
            # Bỏ luôn việc đang chờ, tránh để ô nhập kẹt ở trạng thái khoá.
            st.session_state.pending_question = None
            st.session_state.pending_mindmap = False
            st.rerun()
