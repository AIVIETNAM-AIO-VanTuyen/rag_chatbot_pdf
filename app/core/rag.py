# app/core/rag.py
import ollama
from app.config import LLM_MODEL, EMBED_MODEL, PROMPT

def embed(texts: list[str]) -> list[list[float]]:
    """Chuyển danh sách chuỗi văn bản thành danh sách vector embedding sử dụng Ollama."""
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    if hasattr(response, 'embeddings'):
        return response.embeddings
    return response["embeddings"]

def rag(question: str, collection, k: int = 4) -> str:
    """Thực hiện luồng RAG hỏi đáp với mô hình LLM thông qua Ollama."""
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
def check_ollama_status() -> tuple[bool, str, list[str]]:
    """
    Kiểm tra xem Ollama có đang chạy không và mô hình cấu hình có sẵn không.
    Trả về: (sẵn_sàng, thông_báo, danh_sách_model_thiếu)
    """
    try:
        models_response = ollama.list()
        
        # Xử lý các phiên bản thư viện ollama khác nhau
        local_models = []
        if isinstance(models_response, dict) and "models" in models_response:
            local_models = [m["name"] for m in models_response["models"]]
        elif hasattr(models_response, "models"):
            local_models = [m.model for m in models_response.models]
        else:
            local_models = []
            
        # Chuẩn hóa tên model (ví dụ "bge-m3:latest" thành cả "bge-m3:latest" và "bge-m3")
        normalized_locals = []
        for m in local_models:
            normalized_locals.append(m)
            if ":" in m:
                normalized_locals.append(m.split(":")[0])
                
        missing = []
        if EMBED_MODEL not in normalized_locals:
            missing.append(EMBED_MODEL)
        if LLM_MODEL not in normalized_locals:
            missing.append(LLM_MODEL)
            
        if missing:
            return False, f"Thiếu mô hình trong Ollama: {', '.join(missing)}", missing
        return True, "Sẵn sàng", []
    except Exception as e:
        return False, f"Không thể kết nối tới Ollama. Hãy chắc chắn rằng ứng dụng Ollama đang chạy! Lỗi: {str(e)}", [EMBED_MODEL, LLM_MODEL]

def pull_model_stream(model_name: str):
    """Tải model từ Ollama library và trả về stream tiến trình."""
    return ollama.pull(model_name, stream=True)

def generate_mindmap(collection) -> str:
    """Tự động phân tích tài liệu và sinh sơ đồ tư duy phân cấp."""
    # Tìm kiếm các đoạn chứa thông tin tổng quan, mục lục hoặc nội dung cốt lõi
    res = collection.query(query_embeddings=embed(["mục lục, tổng quan, tóm tắt, các chương chính"]), n_results=6)
    context = "\n\n".join(res["documents"][0])
    
    prompt = f"""Bạn là chuyên gia phân tích tài liệu. Hãy tạo một sơ đồ tư duy (mindmap) chi tiết, khoa học và dễ hiểu dựa trên ngữ cảnh được cung cấp dưới đây.
Sơ đồ tư duy cần bao gồm các nhánh chính (chủ đề lớn) và các nhánh con (chi tiết bổ trợ).

Yêu cầu định dạng:
Trình bày dưới dạng danh sách cây phân cấp bằng Markdown (thụt lề rõ ràng bằng tab hoặc dấu cách, dùng các ký hiệu như └──, ├──).

Ngữ cảnh tài liệu:
{context}

Hãy viết toàn bộ bằng tiếng Việt, ngắn gọn, súc tích và tập trung vào cấu trúc tài liệu.
"""
    
    resp = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": 0.2,
            "num_ctx": 4096,
            "num_predict": -1
        },
    )
    return resp["message"]["content"]
