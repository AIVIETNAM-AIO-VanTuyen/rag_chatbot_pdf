# app/core/rag.py
import time
import json
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

        mindmap_prompt = """You are a professional AI expert skilled in converting document content into hierarchical mindmap structures in JSON format.
Your task is to read the provided document context and transform it into a well-organized JSON object representing the mindmap, including the core definitions, concepts, or explanations.

STRICT MANDATORY RULES:
1. Do NOT write any introduction, explanation, or markdown. Output ONLY valid JSON.
2. Return a JSON object with "title" (string) and "nodes" (array) fields.
3. Each node object must have: {{"id": string, "label": string (Vietnamese only), "parent": string or null, "description": string or null}}
4. Keep node labels concise (2-4 words) for topics/categories. 
5. For leaf nodes or nodes representing specific concepts, terms, definitions, or details in the document, provide a short, clear, and informative explanation (1-2 sentences in Vietnamese) in the "description" field. For grouping nodes, folders, or high-level categories, set "description" to null.
6. Use hierarchical parent-child relationships.
7. Ensure the JSON is valid and properly formatted.

EXAMPLE:
If the document is about: "A software project that includes frontend development, backend API services, and database management with security protocols."
You must return exactly:
{{
    "title": "Dự án phần mềm",
    "nodes": [
        {{"id": "1", "label": "Dự án phần mềm", "parent": null, "description": null}},
        {{"id": "2", "label": "Thành phần chính", "parent": "1", "description": null}},
        {{"id": "3", "label": "Frontend", "parent": "2", "description": "Giao diện người dùng được xây dựng bằng HTML, CSS, và React JS."}},
        {{"id": "4", "label": "Backend API", "parent": "2", "description": "Hệ thống dịch vụ API xử lý logic nghiệp vụ viết bằng Python FastAPI."}},
        {{"id": "5", "label": "Quản lý dữ liệu", "parent": "2", "description": "Lưu trữ dữ liệu có cấu trúc với PostgreSQL và cấu hình cơ chế sao lưu."}},
        {{"id": "6", "label": "Giao thức bảo mật", "parent": "5", "description": "Áp dụng mã hóa SSL/TLS cho đường truyền và hash mật khẩu bằng bcrypt."}}
    ]
}}

Document content to analyze:
{context}

JSON mindmap:"""

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
            response_text = self.get_response_text(resp)
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If response is not valid JSON, try to extract JSON from it
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                raise ValueError("Không thể parse JSON từ response của Gemini.")
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
            response_text = resp["message"]["content"]
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If response is not valid JSON, try to extract JSON from it
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                raise ValueError("Không thể parse JSON từ response của Ollama.")

# Khởi tạo instance dùng chung cho toàn dự án (Singleton Pattern)
ai_service = AIService()
