# app/services/pdf_service.py
import os
import tempfile
import pypdf
from app.core.database import db_manager
from app.core.rag import ai_service

class PDFProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """Khởi tạo cấu hình cho bộ xử lý tài liệu PDF."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text_with_page(self, text: str, page_num: int) -> list[str]:
        """Cắt nhỏ văn bản của từng trang dựa trên cấu hình chunk_size và chunk_overlap."""
        paras = [p.strip() for p in text.split("\n") if p.strip()]
        chunks, cur = [], ""
        page_prefix = f"[Văn bản thuộc Trang {page_num}] "
        
        for p in paras:
            if len(cur) + len(p) + 1 <= self.chunk_size:
                cur += p + "\n"
            else:
                if cur:
                    chunks.append(page_prefix + cur.strip())
                cur = (cur[-self.chunk_overlap:] + p + "\n") if self.chunk_overlap else (p + "\n")
                
        if cur.strip():
            chunks.append(page_prefix + cur.strip())
            
        # In debug dữ liệu sau khi cắt
        print(f"\n--- [DEBUG] Kết quả cắt văn bản Trang {page_num} ({len(chunks)} chunks) ---")
        for idx, chunk in enumerate(chunks):
            print(f"  Chunk {idx + 1} (Độ dài {len(chunk)} ký tự):")
            print(f"    {repr(chunk)}")
        print("------------------------------------------------------------------\n")
        
        return chunks

    def process(self, uploaded_file) -> tuple:
        """Đọc file PDF, trích xuất text, chunk dữ liệu, tạo embeddings và lưu vào ChromaDB."""
        col_name = db_manager.sanitize_collection_name(uploaded_file.name)
        client = db_manager.get_client()
        
        # Xóa sạch các collection cũ để đảm bảo chỉ cho phép hỏi đáp trong tài liệu vừa tải lên
        try:
            for existing_col in client.list_collections():
                client.delete_collection(existing_col.name)
        except Exception:
            pass

        # Tạo file tạm để đọc dữ liệu
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            path = tmp.name

        try:
            reader = pypdf.PdfReader(path)
            all_chunks = []
            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                page_text = page.extract_text() or ""
                if page_text.strip():
                    all_chunks.extend(self.chunk_text_with_page(page_text, page_num))
        finally:
            # Luôn đảm bảo xóa file tạm ngay cả khi có lỗi đọc PDF
            if os.path.exists(path):
                os.unlink(path)

        if not all_chunks:
            all_chunks = ["Tài liệu trống hoặc không thể trích xuất chữ."]

        # Xác định engine embedding sử dụng
        use_gemini = False
        if not ai_service.is_ollama_available() and ai_service.gemini_client is not None:
            use_gemini = True

        embedding_model = "gemini" if use_gemini else "ollama"
        col = client.get_or_create_collection(
            name=col_name,
            metadata={"embedding_model": embedding_model}
        )
        col.add(
            ids=[str(i) for i in range(len(all_chunks))],
            documents=all_chunks,
            embeddings=ai_service.embed(all_chunks, force_gemini=use_gemini)
        )
        return col, len(all_chunks)
