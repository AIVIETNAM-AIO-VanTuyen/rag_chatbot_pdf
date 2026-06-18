# 📚 PDF RAG Chatbot with Streamlit

Dự án **PDF RAG Chatbot** là một ứng dụng hỏi đáp thông minh dựa trên nội dung các tài liệu PDF do người dùng tải lên. Ứng dụng sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)** để trích xuất ngữ cảnh chính xác từ tài liệu và trả lời câu hỏi thông qua mô hình ngôn ngữ lớn (LLM) chạy cục bộ.

Ứng dụng được thiết kế theo cấu trúc modular rõ ràng, dễ bảo trì và có giao diện hiện đại phong cách Glassmorphism.

---

## 🛠️ Công nghệ sử dụng

1. **Frontend & App Framework**: [Streamlit](https://streamlit.io/) (Python)
2. **Vector Database**: [ChromaDB](https://www.trychroma.com/) (lưu trữ cục bộ dưới ổ cứng)
3. **Mô hình nhúng (Embedding Model)**: `bge-m3` (chạy qua Ollama)
4. **Mô hình ngôn ngữ (LLM)**: `vicuna:7b-v1.5-q5_1` (chạy qua Ollama)
5. **Trích xuất PDF**: `pypdf`

---

## 📂 Cấu trúc thư mục dự án

```text
rag_chatbot_pdf/
├── app.py                     # Điểm chạy chính (Main Entrypoint)
├── app/                       # Thư mục chứa mã nguồn chính
│   ├── config.py              # Cấu hình Model, Prompt, Đường dẫn VectorDB
│   ├── auth/                  # Quản lý xác thực người dùng
│   │   └── service.py
│   ├── core/                  # Core RAG và Database
│   │   ├── database.py
│   │   └── rag.py
│   ├── services/              # Xử lý nghiệp vụ PDF
│   │   └── pdf_service.py
│   └── ui/                    # Các màn hình giao diện (Streamlit Views)
│       ├── chat_view.py
│       └── login_view.py
├── data/                      # Lưu trữ dữ liệu
│   └── chroma_db/             # Cơ sở dữ liệu Vector (ChromaDB)
├── requirements.txt           # Danh sách thư viện phụ thuộc
└── README.md                  # Hướng dẫn dự án
```

---

## 🚀 Hướng dẫn cài đặt & Chạy ứng dụng

### 1. Yêu cầu hệ thống
- Máy tính đã cài đặt **Python 3.9+**.
- Đã cài đặt **Ollama** và tải về các mô hình tương ứng:
  ```bash
  # Tải mô hình Embedding
  ollama pull bge-m3
  
  # Tải mô hình LLM
  ollama pull vicuna:7b-v1.5-q5_1
  ```

### 2. Thiết lập môi trường ảo và cài đặt thư viện
Tại thư mục gốc của dự án, mở terminal và chạy:

```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
# Trên macOS / Linux:
source .venv/bin/activate
# Trên Windows:
# .venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 3. Khởi chạy ứng dụng
Chạy ứng dụng bằng lệnh sau:
```bash
streamlit run app.py
```

Ứng dụng sẽ tự động mở trên trình duyệt tại địa chỉ mặc định: `http://localhost:8501`.

---

## 🔐 Tài khoản đăng nhập demo

Sau khi khởi chạy, màn hình đăng nhập (Login View) sẽ hiển thị. Cậu có thể sử dụng tài khoản mặc định sau để truy cập:

- **Tên đăng nhập:** `admin`
- **Mật khẩu:** `admin123`

---

## 💡 Các tính năng nổi bật

- **Tải lên & Xử lý PDF**: Tự động bóc tách, chia nhỏ văn bản (chunking) theo trang và lưu trữ lâu dài dưới dạng vector.
- **Thư viện tài liệu**: Sidebar cho phép chọn nhanh các tài liệu đã được lập chỉ mục trước đó mà không cần upload lại.
- **Trò chuyện ngữ cảnh**: RAG tự động tìm kiếm thông tin liên quan nhất và kết xuất câu trả lời chính xác, kèm số trang tham chiếu từ tài liệu gốc.
- **Quản lý hội thoại**: Xóa lịch sử chat chỉ bằng một nút bấm hoặc đổi ngữ cảnh tự động khi chuyển đổi tài liệu.
- **Giao diện Glassmorphism**: Thiết kế bắt mắt, phông chữ Outfit sang trọng và hiệu ứng chuyển đổi mượt mà.
