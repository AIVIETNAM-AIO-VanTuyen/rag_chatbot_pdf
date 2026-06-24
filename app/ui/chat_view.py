# app/ui/chat_view.py
import streamlit as st
from app.core.rag import ai_service
from app.services.pdf_service import PDFProcessor
from app.auth.service import logout

def clean_error(ex: Exception) -> str:
    """Loại bỏ link tải Ollama trong thông báo lỗi nếu có."""
    msg = str(ex)
    for link in [" https://ollama.com/download", "https://ollama.com/download"]:
        msg = msg.replace(link, "")
    return msg.strip()

def show_chat_view():
    """Hiển thị giao diện chính ứng dụng RAG Chatbot."""
    # Khởi tạo các trạng thái session state cho chat
    for k, v in {
        "collection": None,
        "pdf_name": "",
        "chat_history": [],
        "mindmap_content": "",
        "show_mindmap": False
    }.items():
        st.session_state.setdefault(k, v)

    # Cấu trúc giao diện & CSS tùy chỉnh để làm nổi bật nét cao cấp
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
        
        /* Cải thiện sidebar */
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        /* Hiệu ứng bo góc và đổ bóng nhẹ cho nút */
        .stButton>button {
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        /* Làm đẹp khối thông tin và trợ lý */
        .doc-badge {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            border: 1px solid rgba(99, 102, 241, 0.2);
            color: #c7d2fe;
            padding: 10px 16px;
            border-radius: 12px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # =========================================================================
    # Thiết kế thanh Sidebar điều khiển bên trái
    # =========================================================================
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px;">
                <span style="font-size: 1.1rem; color: #a5b4fc; font-weight: 600;">👤 Admin:</span> 
                <span style="font-size: 1.1rem; color: #ffffff; font-weight: 700;">{st.session_state.username}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            logout()
            st.rerun()
            

 
        st.write("---")
        st.subheader("📥 Nạp thêm tài liệu mới")
        f = st.file_uploader("Chọn file PDF mới", type="pdf")
        
        if f and st.button("🚀 Xử lý và Thêm vào thư viện", use_container_width=True, type="primary"):
            with st.spinner("Đang phân tích và index dữ liệu..."):
                try:
                    # Khởi tạo bộ xử lý PDF (OOP) và tiến hành trích xuất
                    processor = PDFProcessor()
                    col, n = processor.process(f)
                    # Nạp thẳng file vừa upload làm ngữ cảnh hiện tại
                    st.session_state.collection = col
                    st.session_state.pdf_name = col.name
                    st.session_state.chat_history = []  
                    st.session_state.mindmap_content = ""
                    st.session_state.show_mindmap = False
                    st.success(f"Đã thêm thành công: {f.name} ({n} chunks)")
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Không thể xử lý file PDF. Lỗi: {clean_error(ex)}")
                
        if st.session_state.collection is not None:
            st.write("---")
            st.subheader("🧠 Phân tích tài liệu")
            if st.button("📊 Xuất sơ đồ tư duy", use_container_width=True, type="primary"):
                st.session_state.show_mindmap = True
                st.rerun()

        st.write("---")
        st.subheader("⚙️ Quản lý cuộc trò chuyện")
        if st.button("🧹 Xóa lịch sử chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    # =========================================================================
    # Khu vực hiển thị Khung Chat (Main UI)
    # =========================================================================
    st.markdown("<h1 style='margin-bottom: 0px;'>📚 Thư Viện Tài Liệu RAG AI</h1>", unsafe_allow_html=True)

    
    # Hiển thị sơ đồ tư duy nếu được chọn
    if st.session_state.get("show_mindmap", False):
        if st.button("⬅️ Quay lại Trò chuyện", type="secondary"):
            st.session_state.show_mindmap = False
            st.rerun()
            
        st.markdown(f"### 🧠 Sơ đồ tư duy tài liệu: **{st.session_state.pdf_name}**")
        
        if not st.session_state.get("mindmap_content"):
            with st.spinner("Đang phân tích nội dung tài liệu và lập sơ đồ tư duy..."):
                try:
                    mindmap = ai_service.generate_mindmap(st.session_state.collection)
                    st.session_state.mindmap_content = mindmap
                    st.rerun()
                except Exception as ex:
                    st.error(f"Lỗi khi tạo sơ đồ tư duy: {clean_error(ex)}")
        else:
            # Xử lý hiển thị dựa trên kiểu dữ liệu của mindmap_content (dict hoặc str)
            mindmap_data = st.session_state.mindmap_content
            
            # Nếu là chuỗi JSON, cố gắng parse sang dict
            if isinstance(mindmap_data, str):
                try:
                    import json
                    mindmap_data = json.loads(mindmap_data)
                except Exception:
                    pass

            # Hàm trích xuất mã Graphviz DOT nếu dữ liệu là chuỗi chứa mã DOT
            def extract_dot_code(text: str) -> str:
                start_idx = text.find("digraph")
                if start_idx != -1:
                    end_idx = text.rfind("}")
                    if end_idx != -1 and end_idx > start_idx:
                        return text[start_idx:end_idx+1]
                return text

            # Hàm chuyển đổi JSON mindmap sang định dạng Graphviz DOT
            def json_to_dot(data: dict, rankdir: str = "LR") -> str:
                import textwrap
                
                def wrap_text(text: str, width: int = 35) -> str:
                    lines = textwrap.wrap(text, width=width)
                    return "\\n".join(lines)
                
                nodes = data.get("nodes", [])
                doc_title = data.get("title")
                
                # Nếu không có title tự nhận diện hoặc là null, dùng tên file làm fallback dự phòng
                if not doc_title or not str(doc_title).strip() or str(doc_title).lower() == "null":
                    doc_title = st.session_state.get("pdf_name", "Tài liệu")
                    if doc_title.lower().endswith(".pdf"):
                        doc_title = doc_title[:-4]
                
                doc_title_escaped = wrap_text(str(doc_title), width=25).replace('"', '\\"')
                
                dot_lines = [
                    "digraph G {",
                    "    // Cấu hình hiển thị sơ đồ đẹp, hiện đại",
                    f'    graph [rankdir={rankdir}, bgcolor="transparent", pad=0.5, nodesep=0.4, ranksep=0.8];',
                    '    node [shape=box, style="filled,rounded", fontname="Arial", margin="0.2,0.1"];',
                    '    edge [color="#6366f1", penwidth=2, arrowhead=normal, arrowsize=0.8];',
                    ""
                ]
                
                # Tập hợp tất cả các ID của các nút hiện có
                existing_ids = {str(node.get("id", "")) for node in nodes if node.get("id")}
                
                # Thêm nút gốc (Tên tài liệu)
                dot_lines.append(f'    "document_root" [label="{doc_title_escaped}", fillcolor="#1e1b4b", color="#818cf8", fontsize=14, penwidth=3, fontcolor="#ffffff"];')
                
                edges = []
                # Khai báo các node và xác định mối quan hệ
                for node in nodes:
                    node_id = str(node.get("id", ""))
                    if not node_id:
                        continue
                    
                    label = str(node.get("label", "")).replace('"', '\\"')
                    parent_id = node.get("parent")
                    description = node.get("description")
                    
                    # Xác định nếu nút này là con trực tiếp của tài liệu gốc
                    is_direct_child_of_root = (
                        parent_id is None or 
                        parent_id == "" or 
                        str(parent_id) == "null" or 
                        str(parent_id) not in existing_ids
                    )
                    
                    if is_direct_child_of_root:
                        edges.append(f'    "document_root" -> "{node_id}";')
                        # Style nút cấp 1 (con trực tiếp của tài liệu gốc)
                        dot_lines.append(f'    "{node_id}" [label="{label}", fillcolor="#312e81", color="#6366f1", fontsize=12, penwidth=2, fontcolor="#ffffff"];')
                    else:
                        edges.append(f'    "{parent_id}" -> "{node_id}";')
                        # Style nút cấp 2 trở đi
                        dot_lines.append(f'    "{node_id}" [label="{label}", fillcolor="#0f172a", color="#475569", fontsize=10, penwidth=1, fontcolor="#cbd5e1"];')
                    
                    # Nếu có mô tả khái niệm (description), tạo nút note chú thích bên cạnh
                    if description and str(description).strip() and str(description).lower() != "null":
                        desc_id = f"desc_{node_id}"
                        wrapped_desc = wrap_text(str(description), width=35).replace('"', '\\"')
                        # Thêm nút note hiển thị thông tin chi tiết
                        dot_lines.append(f'    "{desc_id}" [label="{wrapped_desc}", shape=note, fillcolor="#f8fafc", color="#cbd5e1", fontsize=9, fontcolor="#334155", style="filled"];')
                        # Nối nét đứt không có mũi tên từ nút khái niệm sang nút chú thích
                        edges.append(f'    "{node_id}" -> "{desc_id}" [style=dashed, color="#94a3b8", arrowhead=none];')
                        
                dot_lines.append("}")
                return "\n".join(dot_lines)

            # Hàm chuyển đổi JSON mindmap sang định dạng Graphviz DOT tỏa hai bên từ tâm
            def json_to_dot_radial(data: dict) -> str:
                import textwrap
                
                def wrap_text(text: str, width: int = 35) -> str:
                    lines = textwrap.wrap(text, width=width)
                    return "\\n".join(lines)
                
                nodes = data.get("nodes", [])
                doc_title = data.get("title")
                
                # Nếu không có title tự nhận diện hoặc là null, dùng tên file làm fallback dự phòng
                if not doc_title or not str(doc_title).strip() or str(doc_title).lower() == "null":
                    doc_title = st.session_state.get("pdf_name", "Tài liệu")
                    if doc_title.lower().endswith(".pdf"):
                        doc_title = doc_title[:-4]
                
                doc_title_escaped = wrap_text(str(doc_title), width=25).replace('"', '\\"')
                
                dot_lines = [
                    "digraph G {",
                    "    // Cấu hình hiển thị sơ đồ tỏa tròn từ tâm bằng Graphviz",
                    '    graph [rankdir=LR, bgcolor="transparent", pad=0.5, nodesep=0.4, ranksep=0.8];',
                    '    node [shape=box, style="filled,rounded", fontname="Arial", margin="0.2,0.1"];',
                    '    edge [color="#6366f1", penwidth=2, arrowhead=normal, arrowsize=0.8];',
                    ""
                ]
                
                # Tập hợp tất cả các ID của các nút hiện có
                existing_ids = {str(node.get("id", "")) for node in nodes if node.get("id")}
                
                # Thêm nút gốc (Tên tài liệu)
                dot_lines.append(f'    "document_root" [label="{doc_title_escaped}", fillcolor="#1e1b4b", color="#818cf8", fontsize=14, penwidth=3, fontcolor="#ffffff"];')
                
                # Phân tích các node con trực tiếp để chia làm 2 bên trái/phải
                direct_children = []
                node_map = {}
                for node in nodes:
                    nid = str(node.get("id", ""))
                    if not nid:
                        continue
                    node_map[nid] = node
                    pid = node.get("parent")
                    is_direct = (pid is None or pid == "" or str(pid) == "null" or str(pid) not in existing_ids)
                    if is_direct:
                        direct_children.append(nid)
                
                # Chia đều
                left_nodes = set()
                right_nodes = set()
                for i, child_id in enumerate(direct_children):
                    if i % 2 == 0:
                        left_nodes.add(child_id)
                    else:
                        right_nodes.add(child_id)
                
                # Xây dựng danh sách kề (parent -> children)
                adj = {nid: [] for nid in node_map}
                for nid, node in node_map.items():
                    pid = str(node.get("parent", ""))
                    if pid in adj:
                        adj[pid].append(nid)
                
                # Hàm đệ quy gán bên cho cây con
                node_side = {}
                def assign_side(nid, side):
                    node_side[nid] = side
                    for cid in adj.get(nid, []):
                        assign_side(cid, side)
                
                for nid in left_nodes:
                    assign_side(nid, "left")
                for nid in right_nodes:
                    assign_side(nid, "right")
                
                edges = []
                # Khai báo các node và xác định mối quan hệ
                for node in nodes:
                    node_id = str(node.get("id", ""))
                    if not node_id:
                        continue
                    
                    label = str(node.get("label", "")).replace('"', '\\"')
                    parent_id = node.get("parent")
                    description = node.get("description")
                    side = node_side.get(node_id, "right") # Mặc định là bên phải nếu không phân loại được
                    
                    is_direct_child_of_root = (
                        parent_id is None or 
                        parent_id == "" or 
                        str(parent_id) == "null" or 
                        str(parent_id) not in existing_ids
                    )
                    
                    if is_direct_child_of_root:
                        if side == "left":
                            edges.append(f'    "{node_id}" -> "document_root" [dir=back];')
                        else:
                            edges.append(f'    "document_root" -> "{node_id}";')
                        # Style nút cấp 1
                        dot_lines.append(f'    "{node_id}" [label="{label}", fillcolor="#312e81", color="#6366f1", fontsize=12, penwidth=2, fontcolor="#ffffff"];')
                    else:
                        if side == "left":
                            edges.append(f'    "{node_id}" -> "{parent_id}" [dir=back];')
                        else:
                            edges.append(f'    "{parent_id}" -> "{node_id}";')
                        # Style nút cấp 2 trở đi
                        dot_lines.append(f'    "{node_id}" [label="{label}", fillcolor="#0f172a", color="#475569", fontsize=10, penwidth=1, fontcolor="#cbd5e1"];')
                    
                    # Nếu có mô tả khái niệm (description), tạo nút note chú thích bên cạnh
                    if description and str(description).strip() and str(description).lower() != "null":
                        desc_id = f"desc_{node_id}"
                        wrapped_desc = wrap_text(str(description), width=35).replace('"', '\\"')
                        # Thêm nút note hiển thị thông tin chi tiết
                        dot_lines.append(f'    "{desc_id}" [label="{wrapped_desc}", shape=note, fillcolor="#f8fafc", color="#cbd5e1", fontsize=9, fontcolor="#334155", style="filled"];')
                        
                        if side == "left":
                            # Với bên trái, nút note nên nằm xa tâm hơn nữa (tức là bên trái nút khái niệm)
                            edges.append(f'    "{desc_id}" -> "{node_id}" [style=dashed, color="#94a3b8", arrowhead=none];')
                        else:
                            # Với bên phải, nút note nằm bên phải nút khái niệm
                            edges.append(f'    "{node_id}" -> "{desc_id}" [style=dashed, color="#94a3b8", arrowhead=none];')
                            
                dot_lines.append("")
                # Thêm các cạnh nối vào đồ thị
                dot_lines.extend(edges)
                
                dot_lines.append("}")
                return "\n".join(dot_lines)



            # Hàm chuyển đổi JSON mindmap sang định dạng Graphviz DOT tỏa tròn bong bóng (twopi)
            def json_to_dot_twopi(data: dict) -> str:
                import textwrap
                
                def wrap_text(text: str, width: int = 20) -> str:
                    lines = textwrap.wrap(text, width=width)
                    return "\\n".join(lines)
                
                nodes = data.get("nodes", [])
                doc_title = data.get("title")
                
                # Nếu không có title tự nhận diện hoặc là null, dùng tên file làm fallback dự phòng
                if not doc_title or not str(doc_title).strip() or str(doc_title).lower() == "null":
                    doc_title = st.session_state.get("pdf_name", "Tài liệu")
                    if doc_title.lower().endswith(".pdf"):
                        doc_title = doc_title[:-4]
                
                doc_title_escaped = wrap_text(str(doc_title), width=15).replace('"', '\\"')
                
                dot_lines = [
                    "digraph G {",
                    "    // Cấu hình hiển thị sơ đồ tỏa tròn bong bóng sạch sẽ bằng Graphviz twopi",
                    '    graph [layout=twopi, ranksep=1.8, ratio=auto, bgcolor="transparent", pad=0.5, root="document_root"];',
                    '    node [shape=oval, style="filled", fontname="Arial", margin="0.15,0.1", penwidth=2];',
                    '    edge [color="#818cf8", penwidth=2, arrowhead=none];',
                    ""
                ]
                
                # Tập hợp tất cả các ID của các nút hiện có
                existing_ids = {str(node.get("id", "")) for node in nodes if node.get("id")}
                
                # Thêm nút gốc (Tên tài liệu) - Hình tròn lớn ở giữa
                dot_lines.append(f'    "document_root" [label="{doc_title_escaped}", fillcolor="#1e1b4b", color="#818cf8", fontsize=13, fontcolor="#ffffff", shape=circle, width=1.5, fixedsize=true];')
                
                edges = []
                # Khai báo các node và xác định mối quan hệ
                for node in nodes:
                    node_id = str(node.get("id", ""))
                    if not node_id:
                        continue
                    
                    label = wrap_text(str(node.get("label", "")), width=20).replace('"', '\\"')
                    parent_id = node.get("parent")
                    description = node.get("description")
                    
                    is_direct_child_of_root = (
                        parent_id is None or 
                        parent_id == "" or 
                        str(parent_id) == "null" or 
                        str(parent_id) not in existing_ids
                    )
                    
                    if is_direct_child_of_root:
                        edges.append(f'    "document_root" -> "{node_id}";')
                        # Style nút cấp 1 (con trực tiếp) - hình oval màu tím đậm chữ trắng
                        dot_lines.append(f'    "{node_id}" [label="{label}", fillcolor="#312e81", color="#6366f1", fontsize=11, fontcolor="#ffffff"];')
                    else:
                        edges.append(f'    "{parent_id}" -> "{node_id}";')
                        # Style nút cấp 2 trở đi - hình oval màu sáng chữ tối
                        dot_lines.append(f'    "{node_id}" [label="{label}", fillcolor="#f8fafc", color="#cbd5e1", fontsize=9, fontcolor="#1e293b", penwidth=1];')
                        
                    # Nếu có mô tả khái niệm (description), tạo nút note chú thích bên cạnh
                    if description and str(description).strip() and str(description).lower() != "null":
                        desc_id = f"desc_{node_id}"
                        wrapped_desc = wrap_text(str(description), width=25).replace('"', '\\"')
                        # Thêm nút note hiển thị thông tin chi tiết
                        dot_lines.append(f'    "{desc_id}" [label="{wrapped_desc}", shape=note, fillcolor="#f8fafc", color="#cbd5e1", fontsize=9, fontcolor="#334155", style="filled"];')
                        # Nối nét đứt không có mũi tên từ nút khái niệm sang nút chú thích
                        edges.append(f'    "{node_id}" -> "{desc_id}" [style=dashed, color="#94a3b8", arrowhead=none];')
                        
                dot_lines.append("")
                # Thêm các cạnh nối vào đồ thị
                dot_lines.extend(edges)
                
                dot_lines.append("}")
                return "\n".join(dot_lines)

            # Bộ chọn kiểu sơ đồ (thiết kế ngang cao cấp)
            map_style = st.radio(
                "🎨 Lựa chọn kiểu sơ đồ hiển thị để demo:",
                [
                    "🧠 Tỏa tròn từ tâm (Graphviz)",
                    "📊 Nhánh ngang (Graphviz)",
                    "📈 Nhánh dọc (Graphviz)"
                ],
                horizontal=True
            )

            # Phân tách giao diện thành 3 Tab chính (Visual Graphviz, Tỏa tròn bong bóng Graphviz, Cấu trúc JSON)
            tab1, tab2, tab3 = st.tabs([
                "🖼️ Sơ đồ trực quan (Visual Diagram)", 
                "💭 Tỏa tròn bong bóng (Graphviz)",
                "📝 Cấu trúc dữ liệu JSON"
            ])
            
            with tab1:
                # Tạo code tương ứng dựa trên kiểu sơ đồ được chọn
                if "tỏa tròn" in map_style.lower():
                    if isinstance(mindmap_data, dict):
                        dot_code = json_to_dot_radial(mindmap_data)
                    else:
                        dot_code = extract_dot_code(str(mindmap_data))
                else:
                    rankdir = "LR" if "nhánh ngang" in map_style.lower() else "TB"
                    if isinstance(mindmap_data, dict):
                        dot_code = json_to_dot(mindmap_data, rankdir=rankdir)
                    else:
                        dot_code = extract_dot_code(str(mindmap_data))
                
                try:
                    st.graphviz_chart(dot_code)
                except Exception as e:
                    st.error(f"Có lỗi khi vẽ sơ đồ bằng Graphviz: {str(e)}")
                    st.code(dot_code, language="dot")
                        
            with tab2:
                # Luôn render sơ đồ tỏa tròn bong bóng sạch sẽ bằng Graphviz twopi
                if isinstance(mindmap_data, dict):
                    dot_radial_code = json_to_dot_twopi(mindmap_data)
                else:
                    dot_radial_code = extract_dot_code(str(mindmap_data))
                
                try:
                    st.graphviz_chart(dot_radial_code)
                except Exception as e:
                    st.error(f"Có lỗi khi vẽ sơ đồ tỏa tròn bằng Graphviz: {str(e)}")
                
                with st.expander("📝 Xem mã nguồn sơ đồ (Graphviz DOT)"):
                    st.code(dot_radial_code, language="dot")

            with tab3:
                if isinstance(mindmap_data, dict):
                    st.json(mindmap_data)
                else:
                    st.code(mindmap_data, language="json")

            if st.button("🔄 Tạo lại sơ đồ tư duy", type="secondary"):
                st.session_state.mindmap_content = ""
                st.rerun()
        return

    
    if st.session_state.pdf_name:
        st.markdown(
            f"<div class='doc-badge'>🤖 Đang hỏi đáp với tài liệu: {st.session_state.pdf_name}</div>", 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='color: #64748b; font-size: 0.95rem; margin-bottom: 1.5rem;'>Vui lòng nạp tài liệu để bắt đầu trò chuyện.</div>", 
            unsafe_allow_html=True
        )

    # Hiển thị các tin nhắn cũ trong lịch sử hội thoại
    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    # Kiểm tra điều kiện nạp tài liệu trước khi cho phép chat
    if st.session_state.collection is None:
        st.info("Vui lòng nạp tài liệu PDF từ thanh bên để bắt đầu hỏi đáp.")
        st.chat_input("Nhập câu hỏi...", disabled=True)
    else:
        q = st.chat_input("Nhập câu hỏi của bạn về nội dung tài liệu...")
        if q:
            st.session_state.chat_history.append({"role": "user", "content": q})
            with st.chat_message("user"):
                st.write(q)
                
            with st.spinner("Đang trích xuất dữ liệu và suy nghĩ..."):
                try:
                    ans = ai_service.query_rag(q, st.session_state.collection)
                    with st.chat_message("assistant"):
                        st.write(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans})
                except Exception as ex:
                    print(ex)
                    st.error(f"❌ Đã có lỗi xảy ra vui lòng thử lại sau.")
