# app/core/rag.py
import time
import ollama
from google import genai
from app.config import (
    LLM_MODEL, 
    EMBED_MODEL, 
    PROMPT, 
    GEMINI_API_KEY, 
    GEMINI_LLM_MODEL, 
    GEMINI_EMBED_MODEL
)

class AIService:
    def __init__(self):
        """Khởi tạo AI Service và nạp Gemini Client nếu có API Key."""
        self.gemini_client = None
        if GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception:
                pass

    @staticmethod
    def is_ollama_available() -> bool:
        """Kiểm tra xem ứng dụng Ollama có đang chạy hay không."""
        try:
            ollama.list()
            return True
        except Exception:
            return False

    @staticmethod
    def get_response_text(resp) -> str:
        """Trích xuất nội dung văn bản từ response của Gemini mà không gây ra cảnh báo non-text parts (thought_signature)."""
        try:
            parts = resp.candidates[0].content.parts
            text_parts = [part.text for part in parts if hasattr(part, "text") and part.text]
            if text_parts:
                return "".join(text_parts)
        except Exception:
            pass
        
        try:
            return resp.text
        except Exception:
            return str(resp)

    def embed(self, texts: list[str], force_gemini: bool = False) -> list[list[float]]:
        """Chuyển danh sách chuỗi văn bản thành danh sách vector embedding."""
        use_gemini = force_gemini
        if not use_gemini:
            if not self.is_ollama_available() and self.gemini_client is not None:
                use_gemini = True

        if use_gemini:
            if self.gemini_client is None:
                raise ValueError("Không thể sử dụng Gemini vì GEMINI_API_KEY chưa được cấu hình hoặc cấu hình sai.")
            
            # Chia nhỏ thành từng batch (ví dụ: tối đa 20 văn bản/lần) để tránh Rate Limit (429) và tràn tải của Gemini
            batch_size = 20
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                max_retries = 5
                response = None
                for attempt in range(max_retries):
                    try:
                        response = self.gemini_client.models.embed_content(
                            model=GEMINI_EMBED_MODEL,
                            contents=batch_texts
                        )
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise e
                        time.sleep(2 ** (attempt + 1))
                
                if hasattr(response, 'embeddings'):
                    for emb in response.embeddings:
                        all_embeddings.append(emb.values)
                else:
                    for emb in response.get("embeddings", []):
                        all_embeddings.append(emb.get("values", []))
                
                if i + batch_size < len(texts):
                    time.sleep(1.0)
                    
            return all_embeddings
        else:
            response = ollama.embed(model=EMBED_MODEL, input=texts)
            if hasattr(response, 'embeddings'):
                return response.embeddings
            return response["embeddings"]

    def query_rag(self, question: str, collection, k: int = 4) -> str:
        """Thực hiện luồng RAG hỏi đáp với mô hình LLM thông qua Ollama hoặc Gemini."""
        metadata = getattr(collection, 'metadata', None) or {}
        embedding_model = metadata.get("embedding_model", "ollama")

        if embedding_model == "gemini":
            if self.gemini_client is None:
                raise ValueError("Tài liệu này được nạp bằng Gemini nhưng hiện tại GEMINI_API_KEY chưa được cấu hình.")
            
            res = collection.query(query_embeddings=self.embed([question], force_gemini=True), n_results=k)
            context = "\n\n".join(res["documents"][0])
            
            prompt_text = PROMPT.format(context=context, question=question)
            max_retries = 3
            resp = None
            for attempt in range(max_retries):
                try:
                    resp = self.gemini_client.models.generate_content(
                        model=GEMINI_LLM_MODEL,
                        contents=prompt_text
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(2 ** attempt)
            return self.get_response_text(resp)
        else:
            if not self.is_ollama_available():
                raise ValueError("Tài liệu này được nạp bằng mô hình Ollama cục bộ nhưng Ollama đang offline. Vui lòng khởi động Ollama trên máy tính của bạn, hoặc nạp lại tài liệu mới bằng Gemini.")
                
            res = collection.query(query_embeddings=self.embed([question], force_gemini=False), n_results=k)
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

    def check_ollama_status(self) -> tuple[bool, str, list[str]]:
        """Kiểm tra trạng thái Ollama và các mô hình cục bộ."""
        try:
            models_response = ollama.list()
            local_models = []
            if isinstance(models_response, dict) and "models" in models_response:
                local_models = [m["name"] for m in models_response["models"]]
            elif hasattr(models_response, "models"):
                local_models = [m.model for m in models_response.models]
            else:
                local_models = []
                
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
            return False, f"Không thể kết nối tới Ollama. Hãy chắc chắn rằng ứng dụng Ollama đang chạy! Lỗi: {str(e)}", []

    @staticmethod
    def pull_model_stream(model_name: str):
        """Tải model từ Ollama library."""
        return ollama.pull(model_name, stream=True)

    def generate_mindmap(self, collection) -> str:
        """Tự động phân tích tài liệu và sinh sơ đồ tư duy phân cấp."""
        metadata = getattr(collection, 'metadata', None) or {}
        embedding_model = metadata.get("embedding_model", "ollama")

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

        if embedding_model == "gemini":
            if self.gemini_client is None:
                raise ValueError("Tài liệu này được nạp bằng Gemini nhưng hiện tại GEMINI_API_KEY chưa được cấu hình.")
            
            res = collection.query(query_embeddings=self.embed(["mục lục, tổng quan, tóm tắt, các chương chính"], force_gemini=True), n_results=6)
            context = "\n\n".join(res["documents"][0])
            
            max_retries = 3
            resp = None
            for attempt in range(max_retries):
                try:
                    resp = self.gemini_client.models.generate_content(
                        model=GEMINI_LLM_MODEL,
                        contents=mindmap_prompt.format(context=context)
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(2 ** attempt)
            return self.get_response_text(resp)
        else:
            if not self.is_ollama_available():
                raise ValueError("Tài liệu này được nạp bằng mô hình Ollama cục bộ nhưng Ollama đang offline. Vui lòng khởi động Ollama trên máy tính của bạn, hoặc nạp lại tài liệu mới bằng Gemini.")
                
            res = collection.query(query_embeddings=self.embed(["mục lục, tổng quan, tóm tắt, các chương chính"], force_gemini=False), n_results=6)
            context = "\n\n".join(res["documents"][0])
            
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

# Khởi tạo instance dùng chung cho toàn dự án (Singleton Pattern)
ai_service = AIService()
