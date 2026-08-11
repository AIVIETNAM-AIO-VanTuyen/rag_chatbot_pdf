# app/domain/json_utils.py
"""Đọc JSON từ output của LLM — vốn hay kèm lời dẫn hoặc khối markdown."""
import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _find_balanced_object(text: str) -> str | None:
    """Tìm object JSON đầu tiên bằng cách đếm ngoặc cân bằng.

    Cách này chuẩn hơn regex `\\{.*\\}` kiểu tham lam của bản cũ: regex đó vơ
    luôn mọi thứ từ dấu `{` đầu tiên tới dấu `}` cuối cùng, nên chỉ cần LLM
    viết thêm một câu có dấu ngoặc nhọn ở sau là hỏng.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for position in range(start, len(text)):
        char = text[position]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : position + 1]

    return None


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Cố gắng đọc một JSON object từ `text`. Trả về None nếu bó tay."""
    if not text:
        return None

    candidates = [text.strip()]

    fenced = _FENCE.search(text)
    if fenced:
        candidates.append(fenced.group(1).strip())

    balanced = _find_balanced_object(text)
    if balanced:
        candidates.append(balanced)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed

    return None
