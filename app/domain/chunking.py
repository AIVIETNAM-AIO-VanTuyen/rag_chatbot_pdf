# app/domain/chunking.py
"""Cắt văn bản thành chunk.

Khác biệt so với bản cũ (`PDFProcessor.chunk_text_with_page`):

1. Có GIỚI HẠN CỨNG: mọi chunk trả về luôn <= `chunk_size`. Bản cũ ghép thẳng
   một đoạn dài vào buffer mà không cắt, nên một đoạn 5000 ký tự tạo ra một
   chunk 5000 ký tự dù `chunk_size` là 1000.
2. Overlap cắt theo RANH GIỚI TỪ, không cắt giữa chừng một từ.
3. Số trang nằm ở `Chunk.page` (metadata) chứ không nhúng chuỗi
   "[Văn bản thuộc Trang N] " vào text — chuỗi đó làm nhiễu vector embedding.
4. Hàm thuần tuý, không phụ thuộc gì, nên test được trực tiếp.
"""
import re

from app.domain.models import Chunk

_WHITESPACE_RUN = re.compile(r"[ \t]+")


def normalize_text(text: str) -> str:
    """Gom khoảng trắng thừa và bỏ dòng rỗng, giữ nguyên cấu trúc xuống dòng."""
    lines = [_WHITESPACE_RUN.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _split_hard(text: str, max_len: int) -> list[str]:
    """Cắt cứng theo ký tự khi một 'từ' đơn lẻ còn dài hơn `max_len`."""
    return [text[i : i + max_len] for i in range(0, len(text), max_len)]


def _split_to_units(text: str, max_len: int) -> list[str]:
    """Tách văn bản thành các đơn vị nhỏ, mỗi đơn vị đảm bảo <= `max_len`.

    Thứ tự ưu tiên tách: dòng -> câu -> từ -> ký tự. Nhờ vậy chunk giữ được
    ranh giới ngữ nghĩa ở mức tốt nhất có thể trước khi phải cắt cứng.
    """
    units: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) <= max_len:
            units.append(line)
            continue

        # Dòng quá dài: thử tách theo câu trước.
        for sentence in re.split(r"(?<=[.!?;:])\s+", line):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_len:
                units.append(sentence)
                continue

            # Câu vẫn quá dài: gom từng từ cho tới khi chạm ngưỡng.
            buffer = ""
            for word in sentence.split(" "):
                if len(word) > max_len:
                    if buffer:
                        units.append(buffer)
                        buffer = ""
                    units.extend(_split_hard(word, max_len))
                    continue
                candidate = f"{buffer} {word}".strip()
                if len(candidate) > max_len:
                    units.append(buffer)
                    buffer = word
                else:
                    buffer = candidate
            if buffer:
                units.append(buffer)
    return units


def _tail_overlap(text: str, overlap: int) -> str:
    """Lấy phần đuôi khoảng `overlap` ký tự, cắt theo ranh giới từ."""
    if overlap <= 0 or not text:
        return ""
    if len(text) <= overlap:
        return text
    tail = text[-overlap:]
    # Bỏ mảnh từ bị cắt dở ở đầu đuôi.
    for separator in ("\n", " "):
        position = tail.find(separator)
        if position != -1:
            return tail[position + 1 :].strip()
    return tail.strip()


def chunk_page(
    text: str,
    page: int,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Cắt văn bản của MỘT trang thành danh sách chunk.

    Bảo đảm: mọi phần tử trả về đều có `len(chunk) <= chunk_size`.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size phải lớn hơn 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap phải nằm trong khoảng [0, chunk_size)")

    normalized = normalize_text(text)
    if not normalized:
        return []

    units = _split_to_units(normalized, chunk_size)
    chunks: list[str] = []
    current = ""

    for unit in units:
        if not current:
            current = unit
            continue

        if len(current) + 1 + len(unit) <= chunk_size:
            current = f"{current}\n{unit}"
            continue

        # Chốt chunk hiện tại rồi mở chunk mới bắt đầu bằng phần overlap.
        chunks.append(current)
        tail = _tail_overlap(current, chunk_overlap)
        # Chỉ giữ overlap khi ghép vào vẫn còn nằm trong giới hạn.
        if tail and len(tail) + 1 + len(unit) <= chunk_size:  # noqa: SIM108 - dạng if/else dễ đọc hơn ternary dài
            current = f"{tail}\n{unit}"
        else:
            current = unit

    if current.strip():
        chunks.append(current)

    return chunks


def chunk_pages(
    pages: list[str],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Cắt toàn bộ tài liệu, giữ lại số trang của từng chunk trong metadata."""
    result: list[Chunk] = []
    for page_index, page_text in enumerate(pages):
        page_number = page_index + 1
        for text in chunk_page(
            page_text,
            page_number,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ):
            result.append(Chunk(text=text, page=page_number, index=len(result)))
    return result
