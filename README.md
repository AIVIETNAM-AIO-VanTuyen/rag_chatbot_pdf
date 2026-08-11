# 📚 PDF RAG Chatbot with Streamlit

Dự án **PDF RAG Chatbot** là một ứng dụng hỏi đáp thông minh dựa trên nội dung tài liệu PDF do người dùng tải lên. Ứng dụng sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)** để trích xuất ngữ cảnh chính xác từ tài liệu và trả lời câu hỏi.

Ứng dụng chạy trên **Google Gemini API** — không cần cài đặt mô hình cục bộ, chỉ cần một API key.

---

## 🛠️ Công nghệ sử dụng

1. **Frontend & App Framework**: [Streamlit](https://streamlit.io/) (Python)
2. **Vector Database**: [ChromaDB](https://www.trychroma.com/) — mặc định chạy **in-memory**, bật `CHROMA_PERSIST_DIR` để lưu xuống ổ cứng
3. **AI Engine**: [Google Gemini](https://ai.google.dev/)
   - Mô hình nhúng (Embedding): `gemini-embedding-001`
   - Mô hình ngôn ngữ (LLM): `gemini-3.5-flash`
4. **Trích xuất PDF**: `pypdf`
5. **Cấu hình**: `pydantic-settings` (đọc `.env`, có kiểm tra hợp lệ)
6. **Vẽ sơ đồ tư duy**: [Graphviz](https://graphviz.org/) tích hợp qua Streamlit

---

## 🏗️ Kiến trúc

Dự án đi theo kiến trúc phân tầng (ports & adapters). Nguyên tắc là **phụ thuộc chỉ hướng vào trong**: `ui` → `usecases` → `domain`, còn `adapters` cắm vào các interface do `domain` định nghĩa.

```text
rag_chatbot_pdf/
├── app.py                        # Điểm chạy Streamlit, chỉ định tuyến màn hình
├── app/
│   ├── domain/                   # Thuần Python — không import streamlit/chromadb/genai
│   │   ├── models.py             # Chunk, DocumentRef, ChatTurn, Answer
│   │   ├── ports.py              # Interface: LLMProvider, EmbeddingProvider, VectorStore
│   │   ├── chunking.py           # Thuật toán cắt chunk
│   │   ├── naming.py             # Sinh tên collection kèm định danh chủ sở hữu
│   │   ├── json_utils.py         # Đọc JSON từ output của LLM
│   │   └── errors.py             # Cây exception nghiệp vụ
│   ├── adapters/                 # Nơi DUY NHẤT được import thư viện bên ngoài
│   │   ├── gemini_provider.py    # LLM + embedding qua Google Gemini
│   │   ├── chroma_store.py       # Vector store
│   │   ├── pdf_loader.py         # Đọc PDF
│   │   └── retry.py              # Thử lại với backoff
│   ├── usecases/                 # Nghiệp vụ — viết một lần, chạy với mọi provider
│   │   ├── ingest_document.py
│   │   ├── answer_question.py
│   │   ├── generate_mindmap.py
│   │   ├── authenticate.py
│   │   ├── retrieval.py          # Phần truy hồi dùng chung
│   │   └── prompts.py            # Toàn bộ prompt gom về một chỗ
│   ├── infra/
│   │   ├── settings.py           # Cấu hình từ .env, có validate
│   │   ├── container.py          # Lắp ráp phụ thuộc
│   │   └── logging.py
│   └── ui/                       # Chỉ render, không chứa logic nghiệp vụ
│       ├── state.py              # Cầu nối Streamlit ↔ container
│       ├── login_view.py
│       ├── chat_view.py
│       ├── sidebar.py
│       ├── mindmap_view.py
│       └── mindmap_dot.py        # Sinh mã Graphviz DOT (thuần, không dùng Streamlit)
├── requirements.txt              # Thư viện chạy app (đã ghim phiên bản)
├── requirements-dev.txt          # Thêm pytest + ruff
└── pyproject.toml                # Cấu hình ruff và pytest
```

**Vì sao chia như vậy**: mọi thứ liên quan tới nhà cung cấp mô hình đều nằm sau hai interface `LLMProvider` và `EmbeddingProvider` trong [`app/domain/ports.py`](app/domain/ports.py). Hai lợi ích cụ thể: test thay được Gemini bằng đối tượng giả nên toàn bộ test chạy offline; và nếu sau này đổi hoặc thêm nhà cung cấp thì chỉ viết thêm một adapter, không đụng tới usecase.

---

## 🚀 Hướng dẫn cài đặt & Chạy ứng dụng

### 1. Yêu cầu hệ thống

- **Python 3.11+**
- **Gemini API key** — lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/)

### 2. Thiết lập môi trường ảo và cài đặt thư viện

```bash
python3 -m venv .venv

# macOS / Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường

```bash
cp .env.example .env
```

Mở `.env` và điền khoá API (bắt buộc):

```env
GEMINI_API_KEY=khóa_api_gemini_của_bạn
```

*(Lấy key tại [Google AI Studio](https://aistudio.google.com/))*

Các tham số khác (kích thước chunk, số đoạn truy hồi, giới hạn file, số lượt hội thoại gửi kèm...) đều chỉnh được trong `.env` — xem `.env.example` để biết danh sách đầy đủ.

### 4. Khởi chạy ứng dụng

```bash
streamlit run app.py
```

Ứng dụng mở tại `http://localhost:8501`.

---

## 🧪 Phát triển

```bash
pip install -r requirements-dev.txt

ruff check app.py app/       # kiểm tra lint
```

Bộ test (115 test, chạy hoàn toàn offline nhờ thay Gemini bằng đối tượng giả) được giữ ở máy local và không nằm trong repo này.

---

## 🔐 Tài khoản đăng nhập demo

- **Tên đăng nhập:** `admin`
- **Mật khẩu:** `admin123`

Đổi được qua `AUTH_USERNAME` / `AUTH_PASSWORD` trong `.env`. Đây vẫn là xác thực tạm cho bản demo — xác thực thật (lưu người dùng trong DB, băm mật khẩu bằng bcrypt) nằm trong kế hoạch nâng cấp.

---

## 💡 Các tính năng nổi bật

- **Kiến trúc ports & adapters**: logic RAG độc lập hoàn toàn với nhà cung cấp mô hình. Thêm provider mới = thêm một file adapter.
- **Cô lập dữ liệu theo phiên**: mỗi phiên trình duyệt có `owner_id` riêng, tên collection mang tiền tố đó. Nhiều người dùng app cùng lúc không xoá đè tài liệu của nhau.
- **Hỏi đáp có ngữ cảnh hội thoại**: N lượt gần nhất được gửi kèm cho LLM, nên các câu hỏi nối tiếp ("giải thích rõ hơn đi", "cái đó là gì") hoạt động đúng.
- **Trích dẫn nguồn**: số trang được lưu ở metadata của vector store và hiển thị dưới mỗi câu trả lời.
- **Xử lý Rate Limit**: nhúng bằng Gemini theo batch nhỏ, có nghỉ giữa batch và thử lại với backoff tăng dần để chịu lỗi 429/503.
- **Tránh lỗi Dimension Mismatch**: tài liệu ghi nhớ model embedding đã dùng lúc nạp; nếu sau này đổi `GEMINI_EMBED_MODEL` thì hệ thống báo lỗi rõ ràng và yêu cầu nạp lại, thay vì trả về kết quả sai âm thầm.
- **Chốt chặn đầu vào**: giới hạn dung lượng, số trang, và báo lỗi rõ ràng với PDF scan ảnh (chưa hỗ trợ OCR) thay vì âm thầm index nội dung rỗng.
- **Xuất Sơ đồ tư duy (Mindmap)**: 4 kiểu hiển thị bằng Graphviz — toả tròn từ tâm, nhánh ngang, nhánh dọc và toả tròn bong bóng (`twopi`), kèm nút ghi chú nét đứt.
- **Giao diện Glassmorphism**: phông chữ Outfit và hiệu ứng chuyển đổi mượt.

---

## 📷 Hình ảnh minh họa sơ đồ tư duy

### 1. Sơ đồ trực quan tỏa hai bên (Visual Diagram)

![Sơ đồ trực quan tỏa hai bên](visual_diagram.png)

### 2. Sơ đồ tỏa tròn bong bóng (Circular Diagram)

![Sơ đồ tỏa tròn bong bóng](circular_diagram.png)
