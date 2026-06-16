import ollama
import os
import tempfile
import pypdf
import chromadb
import time
from app.config import EMBED_MODEL,LLM_MODEL,PROMPT

def embed(texts):
    """Chuyển danh sách chuỗi văn bản thành danh sách vector embedding."""
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    if hasattr(response, 'embeddings'):
        return response.embeddings
    return response["embeddings"]


def chunk_text_with_page(text, page_num, size=1000, overlap=200):
    """Cắt nhỏ văn bản của từng trang và chèn số trang vào đầu mỗi chunk để giữ ngữ cảnh."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, cur = [], ""
    
    # Tiêu đề ngữ cảnh để AI biết đoạn này nằm ở trang nào
    page_prefix = f"[Văn bản thuộc Trang {page_num}] "
    
    for p in paras:
        # Đảm bảo độ dài bao gồm cả tiền tố số trang
        if len(cur) + len(p) + 1 <= size:
            cur += p + "\n"
        else:
            if cur:
                chunks.append(page_prefix + cur.strip())
            cur = (cur[-overlap:] + p + "\n") if overlap else (p + "\n")
            
    if cur.strip():
        chunks.append(page_prefix + cur.strip())
    return chunks


def process_pdf(uploaded_file):
    """Xử lý PDF theo từng trang: Trích xuất, cắt đoạn kèm số trang và lưu vào database."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        path = tmp.name

    # Đọc file PDF
    reader = pypdf.PdfReader(path)
    all_chunks = []
    
    # Duyệt qua từng trang một
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1 # Số trang thực tế (bắt đầu từ 1)
        page_text = page.extract_text() or ""
        
        if page_text.strip():
            # Cắt nhỏ văn bản của trang hiện tại và chèn thẻ số trang
            page_chunks = chunk_text_with_page(page_text, page_num)
            all_chunks.extend(page_chunks)
            
    os.unlink(path) # Xóa file tạm

    if not all_chunks:
        all_chunks = ["Tài liệu trống hoặc không thể trích xuất chữ."]

    # Lưu toàn bộ các chunk đã chuẩn hóa ngữ cảnh vào ChromaDB
    client = chromadb.Client()
    col = client.get_or_create_collection(f"rag_{int(time.time())}")
    col.add(
        ids=[str(i) for i in range(len(all_chunks))],
        documents=all_chunks,
        embeddings=embed(all_chunks)
    )
    return col, len(all_chunks)

def rag(question, collection, k=4):
    """Thực hiện luồng RAG: Tìm kiếm văn bản liên quan và gửi kèm câu hỏi cho LLM."""
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