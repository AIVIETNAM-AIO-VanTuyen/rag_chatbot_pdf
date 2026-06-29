# app/ui/utils.py

def clean_error(ex: Exception) -> str:
    """Loại bỏ link tải Ollama trong thông báo lỗi nếu có."""
    msg = str(ex)
    for link in [" https://ollama.com/download", "https://ollama.com/download"]:
        msg = msg.replace(link, "")
    return msg.strip()
