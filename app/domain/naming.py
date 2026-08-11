# app/domain/naming.py
"""Sinh tên collection cho ChromaDB, có gắn định danh chủ sở hữu.

Mỗi phiên Streamlit có một `owner_id` riêng và tên collection luôn mang tiền tố
đó. Nhờ vậy một phiên chỉ nhìn thấy và chỉ xoá được tài liệu của chính mình —
đây là phần cốt lõi vá bug "upload của user B xoá sạch tài liệu của user A".

Ràng buộc tên collection của ChromaDB: dài 3-63 ký tự, chỉ gồm [a-zA-Z0-9._-],
bắt đầu và kết thúc bằng ký tự chữ hoặc số.
"""
import re

MAX_NAME_LENGTH = 63
OWNER_PREFIX_LENGTH = 8
_INVALID_CHARS = re.compile(r"[^a-zA-Z0-9_-]")
_REPEATED_UNDERSCORE = re.compile(r"_+")


def slugify(name: str) -> str:
    """Chuẩn hoá tên file thành mảnh tên hợp lệ (chưa gắn tiền tố owner)."""
    slug = _INVALID_CHARS.sub("_", name)
    slug = _REPEATED_UNDERSCORE.sub("_", slug).strip("_-")
    return slug or "doc"


def owner_prefix(owner_id: str) -> str:
    """Rút gọn `owner_id` thành tiền tố ngắn, an toàn cho tên collection."""
    prefix = _INVALID_CHARS.sub("", owner_id)[:OWNER_PREFIX_LENGTH]
    return prefix or "anon"


def build_collection_name(display_name: str, owner_id: str) -> str:
    """Ghép tiền tố owner với tên tài liệu, cắt gọn cho vừa giới hạn của Chroma."""
    prefix = owner_prefix(owner_id)
    budget = MAX_NAME_LENGTH - len(prefix) - 1
    slug = slugify(display_name)[:budget].strip("_-")
    name = f"{prefix}_{slug}" if slug else prefix
    if len(name) < 3:
        name = f"{name}_doc"
    return name[:MAX_NAME_LENGTH].strip("_-")


def belongs_to(collection_name: str, owner_id: str) -> bool:
    """Kiểm tra collection có thuộc về `owner_id` hay không."""
    return collection_name.startswith(f"{owner_prefix(owner_id)}_")
