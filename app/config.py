# app/config.py

# Cấu hình định danh mô hình sử dụng
LLM_MODEL = "vicuna:7b-v1.5-q5_1"
EMBED_MODEL = "bge-m3"

# Thư mục vật lý trên ổ cứng để lưu trữ Vector Database
CHROMA_DB_DIR = "./data/chroma_db"

# Template Prompt hướng dẫn cấu trúc câu trả lời cho LLM
PROMPT = """Bạn là trợ lý hỏi đáp. Dùng các đoạn ngữ cảnh dưới đây để trả lời câu hỏi.
1. Nếu ngữ cảnh không có thông tin, hãy nói là bạn không biết, đừng bịa.
2. Trả lời ngắn gọn, chính xác, bằng tiếng Việt.

Ngữ cảnh: {context}

Câu hỏi: {question}
Trả lời: """