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
