# app/services/pdf_service.py
import os
import tempfile
import pypdf
from app.core.database import get_chroma_client, sanitize_collection_name
from app.core.rag import embed

def chunk_text_with_page(text: str, page_num: int, size: int = 1000, overlap: int = 200) -> list[str]:
    """Cắt nhỏ văn bản của từng trang và chèn số trang vào đầu mỗi chunk."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, cur = [], ""
    page_prefix = f"[Văn bản thuộc Trang {page_num}] "
    
    for p in paras:
        if len(cur) + len(p) + 1 <= size:
            cur += p + "\n"
        else:
            if cur:
                chunks.append(page_prefix + cur.strip())
            cur = (cur[-overlap:] + p + "\n") if overlap else (p + "\n")
            
    if cur.strip():
        chunks.append(page_prefix + cur.strip())
        
    # In debug dữ liệu sau khi cắt
    print(f"\n--- [DEBUG] Kết quả cắt văn bản Trang {page_num} ({len(chunks)} chunks) ---")
    for idx, chunk in enumerate(chunks):
        print(f"  Chunk {idx + 1} (Độ dài {len(chunk)} ký tự):")
        print(f"    {repr(chunk)}")
    print("------------------------------------------------------------------\n")
    
    return chunks

def process_pdf(uploaded_file):
    """Đọc file PDF, trích xuất text theo trang, chunk dữ liệu, tạo embeddings và lưu vào ChromaDB."""
    col_name = sanitize_collection_name(uploaded_file.name)
    client = get_chroma_client()
    
    # Nếu file đã tồn tại và đã từng được trích xuất, trả về collection và số lượng chunk
    try:
        col = client.get_collection(name=col_name)
        return col, col.count()
    except Exception:
        pass

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        path = tmp.name

    reader = pypdf.PdfReader(path)
    all_chunks = []
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        if page_text.strip():
            all_chunks.extend(chunk_text_with_page(page_text, page_num))
            
    os.unlink(path)

    if not all_chunks:
        all_chunks = ["Tài liệu trống hoặc không thể trích xuất chữ."]

    col = client.get_or_create_collection(col_name)
    col.add(
        ids=[str(i) for i in range(len(all_chunks))],
        documents=all_chunks,
        embeddings=embed(all_chunks)
    )
    return col, len(all_chunks)
