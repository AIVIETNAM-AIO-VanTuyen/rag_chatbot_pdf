# app/usecases/__init__.py
"""Tầng usecase: nghiệp vụ của ứng dụng.

Mỗi usecase chỉ phụ thuộc vào các Protocol trong `app.domain.ports`, nên viết
một lần là chạy được với mọi provider và test được bằng đối tượng giả.
"""
