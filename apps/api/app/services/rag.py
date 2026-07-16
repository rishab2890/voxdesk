"""Knowledge-base pipeline: parse → chunk → embed → store in Qdrant.
Retrieval prefers vector search; falls back to a DB keyword scan when
Qdrant is unavailable, so the platform degrades instead of breaking."""

import io
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Document, DocumentChunk
from app.providers.registry import get_embeddings

log = logging.getLogger(__name__)
COLLECTION = "voxdesk_chunks"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf") or content_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="ignore")


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    # ponytail: fixed-size char chunking; swap for sentence-aware splitting if retrieval quality lags.
    text = " ".join(text.split())
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def _qdrant():
    from qdrant_client import AsyncQdrantClient

    return AsyncQdrantClient(url=get_settings().qdrant_url, timeout=5)


async def _ensure_collection(client, dims: int) -> None:
    from qdrant_client.models import Distance, VectorParams

    if not await client.collection_exists(COLLECTION):
        await client.create_collection(COLLECTION, vectors_config=VectorParams(size=dims, distance=Distance.COSINE))


async def ingest_document(db: AsyncSession, document: Document, data: bytes) -> None:
    """Parse + chunk + embed one document. Called inline on upload or by the worker."""
    document.status = "processing"
    await db.flush()
    try:
        chunks = chunk_text(extract_text(document.filename, document.content_type, data))
        embedder = get_embeddings()
        vectors = await embedder.embed(chunks) if chunks else []

        rows = []
        for i, (content, _vec) in enumerate(zip(chunks, vectors)):
            rows.append(
                DocumentChunk(
                    organization_id=document.organization_id,
                    document_id=document.id,
                    position=i,
                    content=content,
                    vector_id=str(uuid.uuid4()),
                )
            )
        db.add_all(rows)

        try:
            from qdrant_client.models import PointStruct

            client = _qdrant()
            await _ensure_collection(client, embedder.dimensions)
            if rows:
                await client.upsert(
                    COLLECTION,
                    points=[
                        PointStruct(
                            id=row.vector_id,
                            vector=vec,
                            payload={
                                "organization_id": document.organization_id,
                                "document_id": document.id,
                                "content": row.content,
                            },
                        )
                        for row, vec in zip(rows, vectors)
                    ],
                )
        except Exception:
            log.warning("Qdrant unavailable, chunks stored in DB only", exc_info=True)

        document.chunk_count = len(rows)
        document.status = "ready"
    except Exception:
        document.status = "failed"
        log.exception("Document ingestion failed: %s", document.id)
    await db.flush()


async def retrieve(db: AsyncSession, organization_id: str, query: str, top_k: int = 4) -> list[dict]:
    """Returns [{content, document_id, score}] scoped to the organization."""
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        embedder = get_embeddings()
        [vector] = await embedder.embed([query])
        client = _qdrant()
        hits = await client.query_points(
            COLLECTION,
            query=vector,
            limit=top_k,
            query_filter=Filter(must=[FieldCondition(key="organization_id", match=MatchValue(value=organization_id))]),
        )
        results = [
            {"content": p.payload["content"], "document_id": p.payload["document_id"], "score": p.score}
            for p in hits.points
        ]
        if results:
            return results
    except Exception:
        log.warning("Qdrant query failed, falling back to keyword search")

    # Fallback: naive keyword overlap on DB chunks.
    rows = (
        await db.execute(
            select(DocumentChunk).where(
                DocumentChunk.organization_id == organization_id, DocumentChunk.deleted_at.is_(None)
            )
        )
    ).scalars().all()
    terms = set(query.lower().split())
    scored = []
    for row in rows:
        score = len(terms & set(row.content.lower().split()))
        if score:
            scored.append({"content": row.content, "document_id": row.document_id, "score": float(score)})
    scored.sort(key=lambda r: -r["score"])
    return scored[:top_k]
