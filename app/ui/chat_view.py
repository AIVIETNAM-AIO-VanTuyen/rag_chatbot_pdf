# app/ui/chat_view.py
import streamlit as st
from app.core.database import get_chroma_client, list_all_documents
from app.core.rag import rag, check_ollama_status, pull_model_stream, generate_mindmap
from app.services.pdf_service import process_pdf
from app.auth.service import logout

def show_chat_view():
    """Hiển thị giao diện chính ứng dụng RAG Chatbot."""
    # Khởi tạo các trạng thái session state cho chat
    for k, v in {
        "collection": None,
        "pdf_name": "",
        "chat_history": [],
        "mindmap_content": "",
        "show_mindmap": False
    }.items():
        st.session_state.setdefault(k, v)

    # Cấu trúc giao diện & CSS tùy chỉnh để làm nổi bật nét cao cấp
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        body, [class*="st-"] {
            font-family: 'Outfit', sans-serif;
        }
        
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
        """,
        unsafe_allow_html=True
    )

    # =========================================================================
    # Thiết kế thanh Sidebar điều khiển bên trái
    # =========================================================================
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
            logout()
            st.rerun()
            
        st.write("---")
        st.subheader("📁 Thư viện tài liệu đã nạp")
        
        # Lấy danh sách các tài liệu hiện có từ Database
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
                st.session_state.mindmap_content = ""
                st.session_state.show_mindmap = False
                st.rerun()
        else:
            st.info("Thư viện hiện đang trống.")
 
        st.write("---")
        st.subheader("📥 Nạp thêm tài liệu mới")
        f = st.file_uploader("Chọn file PDF mới", type="pdf")
        
        if f and st.button("🚀 Xử lý và Thêm vào thư viện", use_container_width=True, type="primary"):
            with st.spinner("Đang phân tích và index dữ liệu..."):
                # Gọi service xử lý file PDF
                col, n = process_pdf(f)
                # Nạp thẳng file vừa upload làm ngữ cảnh hiện tại
                st.session_state.collection = col
                st.session_state.pdf_name = col.name
                st.session_state.chat_history = []  
                st.session_state.mindmap_content = ""
                st.session_state.show_mindmap = False
                st.success(f"Đã thêm thành công: {f.name}")
                st.rerun()
                
        if st.session_state.collection is not None:
            st.write("---")
            st.subheader("🧠 Phân tích tài liệu")
            if st.button("📊 Xuất sơ đồ tư duy", use_container_width=True, type="primary"):
                st.session_state.show_mindmap = True
                st.rerun()

        st.write("---")
        st.subheader("⚙️ Quản lý cuộc trò chuyện")
        if st.button("🧹 Xóa lịch sử chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    # =========================================================================
    # Khu vực hiển thị Khung Chat (Main UI)
    # =========================================================================
    st.markdown("<h1 style='margin-bottom: 0px;'>📚 Thư Viện Tài Liệu RAG AI</h1>", unsafe_allow_html=True)
    
    # Kiểm tra trạng thái kết nối và các mô hình của Ollama
    ollama_ok, ollama_msg, missing_models = check_ollama_status()
    if not ollama_ok:
        st.warning(f"⚠️ **Thông báo hệ thống:** {ollama_msg}")
        if missing_models:
            st.info("Hệ thống có thể tự động tải các mô hình này về máy cho bạn. Vui lòng đảm bảo ứng dụng Ollama đã được mở trên máy tính.")
            for m_name in missing_models:
                if st.button(f"📥 Tải mô hình '{m_name}' về Ollama", key=f"pull_{m_name}", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    try:
                        for progress in pull_model_stream(m_name):
                            if isinstance(progress, dict) and 'total' in progress and progress['total'] > 0:
                                percent = int(progress['completed'] / progress['total'] * 100)
                                progress_bar.progress(percent)
                                status_text.text(f"Đang tải {m_name}: {percent}% ({progress['completed']}/{progress['total']} bytes)")
                            else:
                                status_text.text(f"Trạng thái: {progress.get('status', 'Đang tải...') if isinstance(progress, dict) else str(progress)}")
                        st.success(f"🎉 Tải thành công mô hình {m_name}! Vui lòng tải lại trang.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Không thể tải tự động mô hình {m_name}. Lỗi: {str(ex)}")
                        st.info(f"Cậu có thể tải thủ công ngoài Terminal bằng lệnh: `ollama pull {m_name}`")
        return

    
    # Hiển thị sơ đồ tư duy nếu được chọn
    if st.session_state.get("show_mindmap", False):
        if st.button("⬅️ Quay lại Trò chuyện", type="secondary"):
            st.session_state.show_mindmap = False
            st.rerun()
            
        st.markdown(f"### 🧠 Sơ đồ tư duy tài liệu: **{st.session_state.pdf_name}**")
        
        if not st.session_state.get("mindmap_content"):
            with st.spinner("Đang phân tích nội dung tài liệu và lập sơ đồ tư duy..."):
                try:
                    mindmap = generate_mindmap(st.session_state.collection)
                    st.session_state.mindmap_content = mindmap
                    st.rerun()
                except Exception as ex:
                    st.error(f"Lỗi khi tạo sơ đồ tư duy: {str(ex)}")
        else:
            st.markdown(
                f"""
                <div style="background: rgba(255, 255, 255, 0.02); padding: 1.5rem 2rem; border-radius: 16px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 1.5rem; line-height: 1.6; font-size: 1.05rem; white-space: pre-wrap; font-family: monospace;">
{st.session_state.mindmap_content}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            if st.button("🔄 Tạo lại sơ đồ tư duy", type="secondary"):
                st.session_state.mindmap_content = ""
                st.rerun()
        return

    
    if st.session_state.pdf_name:
        st.markdown(
            f"<div class='doc-badge'>🤖 Đang hỏi đáp với tài liệu: {st.session_state.pdf_name}</div>", 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='color: #64748b; font-size: 0.95rem; margin-bottom: 1.5rem;'>Vui lòng nạp tài liệu để bắt đầu trò chuyện.</div>", 
            unsafe_allow_html=True
        )

    # Hiển thị các tin nhắn cũ trong lịch sử hội thoại
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    # Kiểm tra điều kiện nạp tài liệu trước khi cho phép chat
    if st.session_state.collection is None:
        st.info("Vui lòng nạp hoặc chọn một tài liệu PDF từ thanh bên để bắt đầu hệ thống hỏi đáp.")
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
