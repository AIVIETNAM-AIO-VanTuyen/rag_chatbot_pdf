# app/adapters/chroma_store.py
"""Adapter ChromaDB cho port `VectorStore`.

Điểm khác biệt quan trọng so với bản cũ: mọi thao tác đều bị giới hạn trong
phạm vi `owner_id`. Bản cũ khi nạp tài liệu mới sẽ duyệt `list_collections()`
rồi xoá SẠCH mọi collection của toàn tiến trình — nghĩa là người dùng B upload
file thì tài liệu của người dùng A cũng bị xoá theo.
"""
from collections.abc import Sequence
from typing import Any

import chromadb

from app.domain.errors import DocumentNotFoundError
from app.domain.models import Chunk, DocumentRef, RetrievedChunk
from app.domain.naming import belongs_to, build_collection_name
from app.infra.logging import get_logger
from app.infra.settings import Settings

logger = get_logger("chroma")


class ChromaVectorStore:
    """Lưu trữ vector bằng ChromaDB, chạy in-memory hoặc lưu xuống ổ cứng."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: chromadb.ClientAPI | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        """Client ChromaDB, khởi tạo lười ở lần dùng đầu tiên."""
        if self._client is None:
            persist_dir = self._settings.chroma_persist_dir
            if persist_dir:
                persist_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Dùng ChromaDB lưu tại %s", persist_dir)
                self._client = chromadb.PersistentClient(path=str(persist_dir))
            else:
                logger.info("Dùng ChromaDB in-memory (dữ liệu mất khi tắt app)")
                self._client = chromadb.EphemeralClient()
        return self._client

    # -- Đọc danh sách ----------------------------------------------------

    def _collection_names(self) -> list[str]:
        """Tên mọi collection hiện có, xử lý được cả hai kiểu trả về của Chroma."""
        try:
            collections = self.client.list_collections()
        except Exception as error:  # noqa: BLE001
            logger.warning("Không liệt kê được collection: %s", error)
            return []
        return [item if isinstance(item, str) else item.name for item in collections]

    def list_documents(self, owner_id: str) -> list[DocumentRef]:
        """Chỉ trả về tài liệu của `owner_id`."""
        refs: list[DocumentRef] = []
        for name in self._collection_names():
            if not belongs_to(name, owner_id):
                continue
            try:
                collection = self.client.get_collection(name)
            except Exception as error:  # noqa: BLE001
                logger.warning("Bỏ qua collection %s: %s", name, error)
                continue
            metadata: dict[str, Any] = collection.metadata or {}
            refs.append(
                DocumentRef(
                    collection_name=name,
                    display_name=str(metadata.get("display_name", name)),
                    embedding_model=str(metadata.get("embedding_model", "")),
                    owner_id=owner_id,
                    chunk_count=int(metadata.get("chunk_count", 0)),
                )
            )
        return refs

    # -- Ghi ---------------------------------------------------------------

    def create_document(
        self,
        *,
        display_name: str,
        owner_id: str,
        embedding_model: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
    ) -> DocumentRef:
        """Tạo collection mới cho tài liệu, sau khi dọn tài liệu cũ CỦA CHÍNH owner."""
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Số chunk ({len(chunks)}) không khớp số vector ({len(embeddings)})"
            )

        # Chỉ dọn tài liệu của owner này, không đụng tới phiên khác.
        self.delete_documents(owner_id)

        name = build_collection_name(display_name, owner_id)
        collection = self.client.create_collection(
            name=name,
            metadata={
                "embedding_model": embedding_model,
                "display_name": display_name,
                "owner_id": owner_id,
                "chunk_count": len(chunks),
            },
            get_or_create=True,
        )
        collection.add(
            ids=[str(chunk.index) for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            # Số trang nằm ở metadata, không nhúng vào text như bản cũ.
            metadatas=[{"page": chunk.page, "index": chunk.index} for chunk in chunks],
            embeddings=[list(vector) for vector in embeddings],
        )
        logger.info(
            "Đã tạo collection %s với %d chunk (%s)", name, len(chunks), embedding_model
        )

        return DocumentRef(
            collection_name=name,
            display_name=display_name,
            embedding_model=embedding_model,
            owner_id=owner_id,
            chunk_count=len(chunks),
        )

    def delete_documents(self, owner_id: str) -> int:
        """Xoá tài liệu của riêng `owner_id`, trả về số collection đã xoá."""
        deleted = 0
        for name in self._collection_names():
            if not belongs_to(name, owner_id):
                continue
            try:
                self.client.delete_collection(name)
                deleted += 1
            except Exception as error:  # noqa: BLE001
                logger.warning("Không xoá được collection %s: %s", name, error)
        if deleted:
            logger.info("Đã xoá %d tài liệu cũ của phiên %s", deleted, owner_id)
        return deleted

    # -- Truy vấn ------------------------------------------------------------

    def search(
        self,
        ref: DocumentRef,
        query_embedding: Sequence[float],
        *,
        k: int,
    ) -> list[RetrievedChunk]:
        """Tìm `k` đoạn gần nhất trong tài liệu `ref`."""
        try:
            collection = self.client.get_collection(ref.collection_name)
        except Exception as error:  # noqa: BLE001
            logger.warning("Không mở được collection %s: %s", ref.collection_name, error)
            raise DocumentNotFoundError(
                f"Tài liệu '{ref.display_name}' không còn trong bộ nhớ.",
                hint="Vui lòng nạp lại tài liệu từ thanh bên.",
            ) from error

        result = collection.query(
            query_embeddings=[list(query_embedding)],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for position, text in enumerate(documents):
            metadata = metadatas[position] if position < len(metadatas) else {}
            distance = distances[position] if position < len(distances) else None
            chunks.append(
                RetrievedChunk(
                    text=text,
                    page=int((metadata or {}).get("page", 0)),
                    distance=float(distance) if distance is not None else None,
                )
            )
        return chunks
