# app/domain/__init__.py
"""Tầng domain: model dữ liệu, interface (ports) và logic thuần Python.

Tầng này KHÔNG được import streamlit, chromadb hay google-genai.
Nhờ vậy toàn bộ logic ở đây test được mà không cần dựng hạ tầng nào.
"""
