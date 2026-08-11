# app/usecases/authenticate.py
"""Usecase: xác thực người dùng.

Vẫn là tài khoản demo như trước, nhưng thông tin đã rút khỏi source code ra
biến môi trường, và phép so sánh dùng `secrets.compare_digest` để không rò rỉ
thông tin qua thời gian so sánh chuỗi.

Xác thực thật (bảng người dùng trong SQLite, băm mật khẩu bằng bcrypt, hết hạn
phiên) nằm ở Phase 3.
"""
import secrets

from app.infra.settings import Settings


def authenticate(username: str, password: str, settings: Settings) -> bool:
    """Trả về True nếu cặp tài khoản/mật khẩu khớp cấu hình."""
    expected_user = settings.auth_username
    expected_password = settings.auth_password

    # So sánh cả hai vế trước khi trả kết quả để thời gian chạy không phụ thuộc
    # vào việc sai ở trường nào.
    user_ok = secrets.compare_digest(username.strip(), expected_user)
    password_ok = secrets.compare_digest(password, expected_password)
    return user_ok and password_ok
