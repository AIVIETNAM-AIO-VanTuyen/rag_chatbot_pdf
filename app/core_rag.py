# app/core_rag.py
import os
import tempfile
import pypdf
import chromadb
import ollama
import re
from app.config import LLM_MODEL, EMBED_MODEL, PROMPT, CHROMA_DB_DIR

def embed(texts):
    """Chuyển danh sách chuỗi văn bản thành danh sách vector embedding."""
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    if hasattr(response, 'embeddings'):
        return response.embeddings
    return response["embeddings"]

def chunk_text_with_page(text, page_num, size=1000, overlap=200):
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
    return chunks

def sanitize_collection_name(name):
    """Chuẩn hóa tên file thành tên collection hợp lệ trong ChromaDB (3-63 ký tự, không ký tự đặc biệt)."""
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    if len(clean_name) < 3:
        clean_name += "_ext"
    return clean_name[:63]

def get_chroma_client():
    """Khởi tạo hoặc gọi lại Client kết nối trực tiếp xuống ổ cứng."""
    return chromadb.PersistentClient(path=CHROMA_DB_DIR)

def process_pdf(uploaded_file):
    """Đọc PDF, cắt nhỏ, tạo embedding và lưu trữ lâu dài xuống ổ cứng."""
    # Tạo tên collection duy nhất dựa trên tên file
    col_name = sanitize_collection_name(uploaded_file.name)
    client = get_chroma_client()
    
    # Kỹ thuật quan trọng: Nếu cấu trúc file này đã từng được trích xuất dưới ổ cứng rồi, gọi lại dùng luôn
    try:
        col = client.get_collection(name=col_name)
        return col, col.count()
    except Exception:
        # Nếu chưa có thì mới tiến hành bóc tách từ đầu
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

def rag(question, collection, k=4):
    """Thực hiện luồng RAG hỏi đáp với mô hình Vicuna."""
    res = collection.query(query_embeddings=embed([question]), n_results=k)
    context = "\n\n".join(res["documents"][0])
    
    resp = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": PROMPT.format(context=context, question=question)}],
        options={
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": -1
        },
    )
    return resp["message"]["content"]

def list_all_documents():
    """Lấy danh sách tất cả các tên collection (tài liệu) đã lưu dưới ổ cứng."""
    client = get_chroma_client()
    try:
        collections = client.list_collections()
        # Trả về danh sách tên các collection
        return [col.name for col in collections]
    except Exception:
        return []