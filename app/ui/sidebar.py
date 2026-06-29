# app/ui/sidebar.py
import streamlit as st
from app.auth.service import logout
from app.services.pdf_service import PDFProcessor
from app.ui.utils import clean_error

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
            logout()
            st.rerun()
            
        st.write("---")
        st.subheader("📥 Nạp thêm tài liệu mới")
        f = st.file_uploader("Chọn file PDF mới", type="pdf")
        
        if f and st.button("🚀 Xử lý và Thêm vào thư viện", use_container_width=True, type="primary"):
            with st.spinner("Đang phân tích và index dữ liệu..."):
                try:
                    # Khởi tạo bộ xử lý PDF (OOP) và tiến hành trích xuất
                    processor = PDFProcessor()
                    col, n = processor.process(f)
                    # Nạp thẳng file vừa upload làm ngữ cảnh hiện tại
                    st.session_state.collection = col
                    st.session_state.pdf_name = col.name
                    st.session_state.chat_history = []  
                    st.session_state.mindmap_content = ""
                    st.session_state.show_mindmap = False
                    st.success(f"Đã thêm thành công: {f.name} ({n} chunks)")
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Không thể xử lý file PDF. Lỗi: {clean_error(ex)}")
                
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
