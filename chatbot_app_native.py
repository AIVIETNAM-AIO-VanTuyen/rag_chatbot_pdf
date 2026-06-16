import streamlit as st
from app.core_rag import get_chroma_client, process_pdf, rag, sanitize_collection_name


for k,v in {"collection": None, "pdf_name": "", "chat_history":[]}.items():
    st.session_state.setdefault(k,v)

# =========================================================================
# Xây dựng giao diện ứng dụng Web (Streamlit UI)
# =========================================================================
st.set_page_config(page_title="PDF RAG Chatbot", layout="wide", initial_sidebar_state="expanded")
st.title("PDF RAG Assistant: Persistent & Smart")
# Thiết kế thanh Sidebar điều khiển bên trái
with st.sidebar:
    st.subheader("Upload tài liệu")
    f = st.file_uploader("Chọn file PDF cần hỏi đáp", type="pdf")
    
    # Trường hợp 1: Người dùng nhấn nút Xử lý PDF chủ động
    if f and st.button("Xử lý PDF", use_container_width=True):
        with st.spinner("Đang phân tích và xử lý tài liệu..."):
            st.session_state.collection, n = process_pdf(f)
            st.session_state.pdf_name = f.name
            st.session_state.chat_history = []  
            st.session_state.is_loaded = True
            st.success(f"Đã nạp thành công: {n} chunks")
            
    # Trường hợp 2: Nếu người dùng Reload trang (F5) nhưng file f vẫn nằm ở uploader
    # Hệ thống tự động nạp lại collection dưới ổ cứng lên mà không bắt bấm nút lại
    elif f and f.name == st.session_state.pdf_name and not st.session_state.is_loaded:
        client = get_chroma_client()
        col_name = sanitize_collection_name(f.name)
        try:
            st.session_state.collection = client.get_collection(name=col_name)
            st.session_state.is_loaded = True
            st.sidebar.success("Đã tự động khôi phục dữ liệu từ ổ cứng!")
        except Exception:
            pass

    # Hiển thị thông tin file hiện tại
    if st.session_state.pdf_name:
        st.info(f"Tài liệu hiện tại: {st.session_state.pdf_name}")
        # THÊM TÍNH NĂNG: Nút xóa tài liệu chủ động
        if st.button("❌ Đổi / Xóa tài liệu này", use_container_width=True):
            st.session_state.collection = None
            st.session_state.pdf_name = ""
            st.session_state.chat_history = []
            st.session_state.is_loaded = False
            st.rerun()
    else:
        st.info("Chưa có tài liệu được nạp")
    
    if st.button("Xóa lịch sử chat", use_container_width=True):
        st.session_state.chat_history = []

# Hiển thị các tin nhắn cũ trong lịch sử hội thoại
for m in st.session_state.chat_history:
    with st.chat_message(m["role"]):
        st.write(m["content"])

# Kiểm tra điều kiện nạp tài liệu trước khi cho phép người dùng nhập câu hỏi
if st.session_state.collection is None:
    st.info("Vui lòng upload và click nút 'Xử lý PDF' ở sidebar trước khi bắt đầu chat.")
    st.chat_input("Nhập câu hỏi...", disabled=True)
else:
    q = st.chat_input("Nhập câu hỏi của bạn về nội dung tài liệu...")
    if q:
        st.session_state.chat_history.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.write(q)
            
        with st.spinner("Đang trích xuất dữ liệu và suy nghĩ..."):
            ans = rag(q, st.session_state.collection)
            
        with st.chat_message("assistant"):
            st.write(ans)
        st.session_state.chat_history.append({"role": "assistant", "content": ans})