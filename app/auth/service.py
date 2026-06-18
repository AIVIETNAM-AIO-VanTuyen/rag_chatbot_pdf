# app/auth/service.py
import streamlit as st

def init_auth_state():
    """Khởi tạo trạng thái đăng nhập trong session_state của Streamlit."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = ""

def login(username, password) -> bool:
    """Xử lý xác thực tài khoản đăng nhập."""
    # Tài khoản demo cố định
    if username == "admin" and password == "admin123":
        st.session_state.authenticated = True
        st.session_state.username = username
        return True
    return False

def logout():
    """Xóa thông tin đăng nhập và reset lại các trạng thái phiên làm việc."""
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.collection = None
    st.session_state.pdf_name = ""
    st.session_state.chat_history = []
