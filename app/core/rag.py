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
    
    mindmap_prompt = """Bạn là một robot chuyên nghiệp chỉ biết biên dịch văn bản thành ngôn ngữ DOT của Graphviz. 
                    Nhiệm vụ của bạn là đọc ngữ cảnh hợp đồng và chuyển nó thành cấu trúc sơ đồ tư duy hình cây.

                    QUY TẮC BẮT BUỘC KHẮT KHE:
                    1. KHÔNG viết lời mở đầu, KHÔNG viết lời giải thích, KHÔNG dùng markdown danh sách (dấu gạch đầu dòng).
                    2. Chỉ trả về duy nhất mã nguồn bắt đầu bằng cụm từ 'digraph G {{' và kết thúc bằng '}}'.
                    3. Các mối quan hệ viết theo cú pháp: "A" -> "B";
                    4. Node text ngắn gọn từ 2-4 từ, dùng tiếng Việt.

                    VÍ DỤ MẪU:
                    Nếu văn bản là: "Hợp đồng giữa bên A và bên B về việc thanh toán trong 3 ngày."
                    Bạn phải trả về chính xác:
                    digraph G {{
                        rankdir=LR;
                        node [shape=box, style=rounded];
                        "Hợp đồng" -> "Bên tham gia";
                        "Bên tham gia" -> "Bên A";
                        "Bên tham gia" -> "Bên B";
                        "Hợp đồng" -> "Thanh toán";
                        "Thanh toán" -> "Trong 3 ngày";
                    }}

                    Nội dung ngữ cảnh tài liệu cần xử lý:
                    {context}

                    Mã DOT sơ đồ tư duy:"""
    
    resp = ollama.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": mindmap_prompt.format(context=context)}],
        options={
            "temperature": 0.2,
            "num_ctx": 4096,
            "num_predict": -1
        },
    )
    return resp["message"]["content"]
