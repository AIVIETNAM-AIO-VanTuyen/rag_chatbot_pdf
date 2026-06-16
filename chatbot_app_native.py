# chatbot_app_native.py
import streamlit as st
from app.core_rag import process_pdf, rag, get_chroma_client, list_all_documents

# Khởi tạo trạng thái phiên làm việc (Session State) cho Streamlit
for k, v in {"collection": None, "pdf_name": "", "chat_history": []}.items():
    st.session_state.setdefault(k, v)

st.set_page_config(page_title="PDF RAG Chatbot", layout="wide", initial_sidebar_state="expanded")
st.title("📚 Thư Viện Tài Liệu RAG AI")

# =========================================================================
# Thiết kế thanh Sidebar điều khiển bên trái
# =========================================================================
with st.sidebar:
    st.subheader("📁 Thư viện tài liệu đã nạp")
    
    # Lấy danh sách các tài liệu hiện có dưới ổ cứng
    existing_docs = list_all_documents()
    
    if existing_docs:
        # Nếu đã chọn một tài liệu trước đó, tìm vị trí của nó để làm mặc định
        default_index = 0
        if st.session_state.pdf_name in existing_docs:
            default_index = existing_docs.index(st.session_state.pdf_name)
            
        # Hộp chọn tài liệu trong thư viện
        selected_doc = st.selectbox(
            "Chọn tài liệu để hỏi đáp:", 
            options=existing_docs,
            index=default_index
        )
        
        # Nếu người dùng đổi lựa chọn trên selectbox, tiến hành nạp ngữ cảnh mới
        if selected_doc != st.session_state.pdf_name:
            client = get_chroma_client()
            st.session_state.collection = client.get_collection(name=selected_doc)
            st.session_state.pdf_name = selected_doc
            st.session_state.chat_history = []  # Reset chat khi đổi tài liệu
            st.rerun()
    else:
        st.info("Thư viện hiện đang trống.")

    st.write("---")
    st.subheader("📥 Nạp thêm tài liệu mới")
    f = st.file_uploader("Chọn file PDF mới", type="pdf")
    
    if f and st.button("Xử lý và Thêm vào thư viện", use_container_width=True):
        with st.spinner("Đang phân tích và index dữ liệu..."):
            # Hàm process_pdf sẽ tự động lấy tên file làm tên collection hợp lệ
            col, n = process_pdf(f)
            # Nạp thẳng file vừa upload làm ngữ cảnh hiện tại
            st.session_state.collection = col
            st.session_state.pdf_name = col.name
            st.session_state.chat_history = []  
            st.success(f"Đã thêm thành công: {f.name}")
            st.rerun()
            
    st.write("---")
    st.subheader("⚙️ Quản lý cuộc trò chuyện")
    if st.button("🧹 Xóa lịch sử chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# =========================================================================
# Khu vực hiển thị Khung Chat (Main UI)
# =========================================================================
if st.session_state.pdf_name:
    st.caption(f"🤖 Bạn đang trò chuyện với tài liệu: **{st.session_state.pdf_name}**")

# Hiển thị các tin nhắn cũ trong lịch sử hội thoại
for m in st.session_state.chat_history:
    with st.chat_message(m["role"]):
        st.write(m["content"])

# Kiểm tra điều kiện nạp tài liệu trước khi cho phép chat
if st.session_state.collection is None:
    st.info("Vui lòng nạp một tài liệu PDF để bắt đầu hệ thống hỏi đáp.")
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