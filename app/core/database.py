# app/core/database.py
import re
import chromadb
from app.config import CHROMA_DB_DIR

def sanitize_collection_name(name: str) -> str:
    """Chuẩn hóa tên file thành tên collection hợp lệ trong ChromaDB (3-63 ký tự, không ký tự đặc biệt)."""
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    if len(clean_name) < 3:
        clean_name += "_ext"
    return clean_name[:63]

def get_chroma_client():
    """Khởi tạo hoặc gọi lại Client kết nối trực tiếp xuống Vector DB."""
    return chromadb.PersistentClient(path=CHROMA_DB_DIR)

def list_all_documents():
    """Lấy danh sách tất cả các tên collection (tài liệu) đã lưu dưới Vector DB."""
    client = get_chroma_client()
    try:
        collections = client.list_collections()
        return [col.name for col in collections]
    except Exception:
        return []
