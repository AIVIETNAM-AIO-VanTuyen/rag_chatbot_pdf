# app/ui/login_view.py
import streamlit as st
from app.auth.service import login

def show_login_view():
    """Hiển thị màn hình đăng nhập với giao diện Glassmorphism hiện đại."""
    # Inject Custom CSS
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        /* Cấu hình chung */
        div.stApp {
            background: radial-gradient(circle at top right, #1e1b4b, #09090b);
        }
        
        /* Container Đăng nhập dạng Glassmorphism */
        .login-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 3rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            max-width: 450px;
            margin: 6rem auto;
            text-align: center;
            font-family: 'Outfit', sans-serif;
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        .login-card:hover {
            transform: translateY(-8px);
            border-color: rgba(99, 102, 241, 0.3);
            box-shadow: 0 30px 60px rgba(99, 102, 241, 0.15);
        }
        
        .login-header {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.05em;
        }
        
        .login-subtitle {
            color: #94a3b8;
            font-size: 0.95rem;
            margin-bottom: 2rem;
            font-weight: 300;
        }
        
        /* Tạo animation nhỏ khi load view */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade {
            animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Sử dụng columns để căn giữa card đăng nhập trong Streamlit
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div class='login-card animate-fade'>
                <div class='login-header'>🔐 RAG CHATBOT</div>
                <div class='login-subtitle'>Nhập tài khoản Admin để truy cập thư viện tài liệu thông minh</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Form đăng nhập chính
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Tài khoản:", value="admin", placeholder="Nhập tên đăng nhập...")
            password = st.text_input("Mật khẩu:", type="password", value="admin123", placeholder="Nhập mật khẩu...")
            submit = st.form_submit_button("🔥 Xác Thực & Đăng Nhập", use_container_width=True)
            
            if submit:
                if login(username, password):
                    st.success("🎉 Xác thực thành công! Đang chuyển hướng...")
                    st.rerun()
                else:
                    st.error("❌ Tài khoản hoặc mật khẩu không đúng!")
