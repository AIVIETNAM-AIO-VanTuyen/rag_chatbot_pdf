import streamlit as st
from app.core_rag import process_pdf, rag


for k,v in {"collection": None, "pdf_name": "", "chat_history":[]}.items():
    st.session_state.setdefault(k,v)

# =========================================================================
# Xây dựng giao diện ứng dụng Web (Streamlit UI)
# =========================================================================
st.set_page_config(page_title="PDF RAG Chatbot", layout="wide", initial_sidebar_state="expanded")
st.title("PDF RAG Assistant: Native")

# Thiết kế thanh Sidebar điều khiển bên trái
with st.sidebar:
    st.subheader("Upload tài liệu")
    f = st.file_uploader("Chọn file PDF cần hỏi đáp", type="pdf")
    if f and st.button("Xử lý PDF", use_container_width=True):
        with st.spinner("Đang phân tích và xử lý tài liệu..."):
            st.session_state.collection, n = process_pdf(f)
            st.session_state.pdf_name = f.name
            st.session_state.chat_history = [] # Reset lịch sử khi đổi file mới
            st.success(f"Đã index thành công: {n} chunks")
            
    st.info(f"Tài liệu hiện tại: {st.session_state.pdf_name}" if st.session_state.pdf_name else "Chưa có tài liệu được nạp")
    
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
        # Lưu và hiển thị câu hỏi của Người dùng
        st.session_state.chat_history.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.write(q)
            
        # Gọi luồng xử lý RAG kết hợp GPU tính toán câu trả lời
        with st.spinner("Đang trích xuất dữ liệu và suy nghĩ..."):
            ans = rag(q, st.session_state.collection)
            
        # Hiển thị và lưu câu trả lời của Trợ lý AI
        with st.chat_message("assistant"):
            st.write(ans)
        st.session_state.chat_history.append({"role": "assistant", "content": ans})