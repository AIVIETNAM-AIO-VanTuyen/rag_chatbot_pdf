# app.py
# Trigger hot reload: them anh minh hoa vao README.md
import streamlit as st
from app.auth.service import init_auth_state
from app.ui.login_view import show_login_view
from app.ui.chat_view import show_chat_view

# Cấu hình trang Streamlit (Phải gọi đầu tiên trước các command Streamlit khác)
st.set_page_config(page_title="PDF RAG Chatbot", layout="wide", initial_sidebar_state="expanded")

# Khởi tạo trạng thái xác thực người dùng
init_auth_state()

# Định tuyến giao diện dựa trên trạng thái đăng nhập
if not st.session_state.authenticated:
    show_login_view()
else:
    show_chat_view()
