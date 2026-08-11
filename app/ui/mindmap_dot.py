# app/ui/mindmap_dot.py
"""Kết xuất sơ đồ tư duy: sang mã Graphviz DOT để vẽ, và sang văn bản để đưa
vào lịch sử hội thoại.

Không phụ thuộc gì vào Streamlit: tiêu đề dự phòng được truyền vào qua tham số
thay vì đọc lén `st.session_state`. Nhờ vậy phần kết xuất test được trực tiếp.
Phần render đặt trong hội thoại nằm ở `app/ui/chat_view.py`.
"""
import textwrap
from collections.abc import Iterator
from typing import Any, NamedTuple

_ROOT_ID = "document_root"


class Node(NamedTuple):
    """Một nút đã chuẩn hoá, sẵn sàng để render."""

    node_id: str
    label: str
    parent_id: str | None
    description: str | None
    is_root_child: bool


def wrap_text(text: str, width: int = 35) -> str:
    """Xuống dòng tự động cho nhãn dài (dùng '\\n' theo cú pháp DOT)."""
    return "\\n".join(textwrap.wrap(text, width=width))


def _escape(text: str) -> str:
    return str(text).replace('"', '\\"')


def _is_blank(value: Any) -> bool:
    """Nhận diện các dạng 'rỗng' mà LLM hay trả về: None, "", "null"."""
    return value is None or not str(value).strip() or str(value).strip().lower() == "null"


def resolve_title(data: dict[str, Any], fallback: str) -> str:
    """Lấy tiêu đề sơ đồ, lùi về tên file (đã bỏ đuôi .pdf) nếu LLM không cho."""
    title = data.get("title")
    if not _is_blank(title):
        return str(title)
    if fallback.lower().endswith(".pdf"):
        fallback = fallback[:-4]
    return fallback or "Tài liệu"


def iter_nodes(data: dict[str, Any]) -> Iterator[Node]:
    """Duyệt các nút hợp lệ, xác định nút nào là con trực tiếp của gốc."""
    raw_nodes = data.get("nodes", []) or []
    existing = {str(n.get("id", "")) for n in raw_nodes if n.get("id")}

    for raw in raw_nodes:
        node_id = str(raw.get("id", ""))
        if not node_id:
            continue
        parent_id = raw.get("parent")
        # Nút mồ côi (parent trỏ tới id không tồn tại) cũng được treo vào gốc.
        is_root_child = _is_blank(parent_id) or str(parent_id) not in existing
        description = raw.get("description")
        # Nhãn giữ nguyên bản thô; việc escape do từng hàm render đảm nhiệm để
        # tránh escape hai lần khi nhãn còn phải đi qua `wrap_text`.
        yield Node(
            node_id=node_id,
            label=str(raw.get("label", "")),
            parent_id=None if is_root_child else str(parent_id),
            description=None if _is_blank(description) else str(description),
            is_root_child=is_root_child,
        )


def _description_node(node: Node, *, width: int) -> str:
    """Khai báo nút ghi chú nét đứt cho phần mô tả của một nút."""
    wrapped = _escape(wrap_text(node.description or "", width=width))
    return (
        f'    "desc_{node.node_id}" [label="{wrapped}", shape=note, '
        'fillcolor="#f8fafc", color="#cbd5e1", fontsize=9, fontcolor="#334155", style="filled"];'
    )


def render_tree(data: dict[str, Any], *, fallback_title: str, rankdir: str = "LR") -> str:
    """Sơ đồ phân nhánh ngang (rankdir=LR) hoặc dọc (rankdir=TB)."""
    title = _escape(wrap_text(resolve_title(data, fallback_title), width=25))

    lines = [
        "digraph G {",
        "    // Cấu hình hiển thị sơ đồ đẹp, hiện đại",
        f'    graph [rankdir={rankdir}, bgcolor="transparent", pad=0.5, nodesep=0.4, ranksep=0.8];',
        '    node [shape=box, style="filled,rounded", fontname="Arial", margin="0.2,0.1"];',
        '    edge [color="#6366f1", penwidth=2, arrowhead=normal, arrowsize=0.8];',
        "",
        f'    "{_ROOT_ID}" [label="{title}", fillcolor="#1e1b4b", color="#818cf8", '
        'fontsize=14, penwidth=3, fontcolor="#ffffff"];',
    ]
    edges: list[str] = []

    for node in iter_nodes(data):
        if node.is_root_child:
            edges.append(f'    "{_ROOT_ID}" -> "{node.node_id}";')
            lines.append(
                f'    "{node.node_id}" [label="{_escape(node.label)}", fillcolor="#312e81", '
                'color="#6366f1", fontsize=12, penwidth=2, fontcolor="#ffffff"];'
            )
        else:
            edges.append(f'    "{node.parent_id}" -> "{node.node_id}";')
            lines.append(
                f'    "{node.node_id}" [label="{_escape(node.label)}", fillcolor="#0f172a", '
                'color="#475569", fontsize=10, penwidth=1, fontcolor="#cbd5e1"];'
            )

        if node.description:
            lines.append(_description_node(node, width=35))
            edges.append(
                f'    "{node.node_id}" -> "desc_{node.node_id}" '
                '[style=dashed, color="#94a3b8", arrowhead=none];'
            )

    lines.append("")
    # Bản cũ dựng danh sách `edges` rồi quên ghép vào output, nên sơ đồ nhánh
    # ngang/dọc hiện ra toàn nút rời rạc, không có một mũi tên nào.
    lines.extend(edges)
    lines.append("}")
    return "\n".join(lines)


def render_radial(data: dict[str, Any], *, fallback_title: str) -> str:
    """Sơ đồ toả hai bên từ tâm: chia đều nhánh cấp 1 sang trái và phải."""
    title = _escape(wrap_text(resolve_title(data, fallback_title), width=25))
    nodes = list(iter_nodes(data))

    # Chia luân phiên các nhánh cấp 1 sang hai bên, rồi lan xuống toàn cây con.
    children: dict[str, list[str]] = {node.node_id: [] for node in nodes}
    for node in nodes:
        if node.parent_id and node.parent_id in children:
            children[node.parent_id].append(node.node_id)

    side_of: dict[str, str] = {}

    def assign(node_id: str, side: str) -> None:
        if node_id in side_of:
            return  # chặn vòng lặp vô hạn nếu LLM trả về quan hệ cha-con vòng tròn
        side_of[node_id] = side
        for child_id in children.get(node_id, []):
            assign(child_id, side)

    root_children = [node.node_id for node in nodes if node.is_root_child]
    for position, node_id in enumerate(root_children):
        assign(node_id, "left" if position % 2 == 0 else "right")

    lines = [
        "digraph G {",
        "    // Cấu hình hiển thị sơ đồ tỏa tròn từ tâm bằng Graphviz",
        '    graph [rankdir=LR, bgcolor="transparent", pad=0.5, nodesep=0.4, ranksep=0.8];',
        '    node [shape=box, style="filled,rounded", fontname="Arial", margin="0.2,0.1"];',
        '    edge [color="#6366f1", penwidth=2, arrowhead=normal, arrowsize=0.8];',
        "",
        f'    "{_ROOT_ID}" [label="{title}", fillcolor="#1e1b4b", color="#818cf8", '
        'fontsize=14, penwidth=3, fontcolor="#ffffff"];',
    ]
    edges: list[str] = []

    for node in nodes:
        side = side_of.get(node.node_id, "right")
        target = _ROOT_ID if node.is_root_child else node.parent_id

        # Nhánh bên trái vẽ ngược chiều (dir=back) để Graphviz đẩy nút sang trái.
        if side == "left":
            edges.append(f'    "{node.node_id}" -> "{target}" [dir=back];')
        else:
            edges.append(f'    "{target}" -> "{node.node_id}";')

        if node.is_root_child:
            lines.append(
                f'    "{node.node_id}" [label="{_escape(node.label)}", fillcolor="#312e81", '
                'color="#6366f1", fontsize=12, penwidth=2, fontcolor="#ffffff"];'
            )
        else:
            lines.append(
                f'    "{node.node_id}" [label="{_escape(node.label)}", fillcolor="#0f172a", '
                'color="#475569", fontsize=10, penwidth=1, fontcolor="#cbd5e1"];'
            )

        if node.description:
            lines.append(_description_node(node, width=35))
            # Ghi chú luôn nằm xa tâm hơn nút mà nó mô tả.
            if side == "left":
                edges.append(
                    f'    "desc_{node.node_id}" -> "{node.node_id}" '
                    '[style=dashed, color="#94a3b8", arrowhead=none];'
                )
            else:
                edges.append(
                    f'    "{node.node_id}" -> "desc_{node.node_id}" '
                    '[style=dashed, color="#94a3b8", arrowhead=none];'
                )

    lines.append("")
    lines.extend(edges)
    lines.append("}")
    return "\n".join(lines)


def summarize_mindmap(
    data: dict[str, Any],
    *,
    fallback_title: str,
    max_nodes: int = 80,
) -> str:
    """Diễn giải sơ đồ thành văn bản có thụt đầu dòng.

    Tin nhắn sơ đồ trong hội thoại hiển thị bằng hình, nhưng LLM thì chỉ đọc
    được chữ. Bản tóm tắt này được lưu kèm tin nhắn để khi người dùng hỏi tiếp
    "sơ đồ trên nói về vấn đề gì", mô hình có cái mà đọc.
    """
    nodes = list(iter_nodes(data))

    children: dict[str, list[Node]] = {}
    roots: list[Node] = []
    for node in nodes:
        if node.is_root_child:
            roots.append(node)
        else:
            children.setdefault(node.parent_id or "", []).append(node)

    lines = [f"[Sơ đồ tư duy] {resolve_title(data, fallback_title)}"]
    visited: set[str] = set()

    def walk(node: Node, depth: int) -> None:
        # `visited` vừa chặn quan hệ cha-con vòng tròn do LLM sinh ra, vừa giữ
        # cho số dòng không vượt quá giới hạn.
        if node.node_id in visited or len(lines) > max_nodes:
            return
        visited.add(node.node_id)

        text = node.label
        if node.description:
            text = f"{text}: {node.description}"
        lines.append(f"{'  ' * depth}- {text}")

        for child in children.get(node.node_id, []):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)

    if len(nodes) > len(visited):
        lines.append(f"  ... (còn {len(nodes) - len(visited)} nhánh nữa)")

    return "\n".join(lines)
