# app.py
"""Điểm chạy chính của ứng dụng Streamlit."""
import streamlit as st

from app.ui.chat_view import show_chat_view
from app.ui.login_view import show_login_view
from app.ui.state import init_session_state

# Phải gọi trước mọi lệnh Streamlit khác.
st.set_page_config(
    page_title="PDF RAG Chatbot",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

if st.session_state.authenticated:
    show_chat_view()
else:
    show_login_view()
