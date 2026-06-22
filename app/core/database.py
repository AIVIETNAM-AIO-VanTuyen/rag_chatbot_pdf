# app/core/database.py
import re
import chromadb

class ChromaDatabaseManager:
    def __init__(self):
        """Khởi tạo trình quản lý cơ sở dữ liệu ChromaDB (In-memory)."""
        self._client = None

    def get_client(self):
        """Trả về ChromaDB client, tự động khởi tạo EphemeralClient nếu chưa có."""
        if self._client is None:
            self._client = chromadb.EphemeralClient()
        return self._client

    @staticmethod
    def sanitize_collection_name(name: str) -> str:
        """Chuẩn hóa tên file thành tên collection hợp lệ trong ChromaDB (3-63 ký tự, không ký tự đặc biệt)."""
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        clean_name = re.sub(r'_+', '_', clean_name)
        clean_name = clean_name[:63]
        clean_name = clean_name.strip('_-')
        if len(clean_name) < 3:
            clean_name = "col_" + clean_name if clean_name else "col"
        return clean_name

    def list_all_documents(self) -> list[str]:
        """Lấy danh sách tất cả các tài liệu hiện có trong bộ nhớ tạm."""
        client = self.get_client()
        try:
            collections = client.list_collections()
            return [col.name for col in collections]
        except Exception:
            return []

# Khởi tạo instance dùng chung cho toàn dự án (Singleton Pattern)
db_manager = ChromaDatabaseManager()
