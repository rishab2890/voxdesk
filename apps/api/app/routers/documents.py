from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select

from app.deps import TenantCtx, audit, get_ctx, require_role
from app.models import Document, DocumentChunk, KnowledgeBase, Role, utcnow
from app.providers.registry import get_storage
from app.schemas import DocumentOut, RetrievedChunk, RetrieveIn
from app.services import rag

router = APIRouter(prefix="/documents", tags=["knowledge-base"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "text/plain", "text/markdown", "text/csv"}


@router.get("", response_model=list[DocumentOut])
async def list_documents(ctx: TenantCtx = Depends(get_ctx)):
    return (
        await ctx.db.execute(
            select(Document).where(Document.organization_id == ctx.organization_id, Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )
    ).scalars().all()


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 20MB")
    content_type = file.content_type or "text/plain"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Allowed: {sorted(ALLOWED_TYPES)}")

    kb = (
        await ctx.db.execute(select(KnowledgeBase).where(KnowledgeBase.organization_id == ctx.organization_id))
    ).scalars().first()
    if kb is None:
        kb = KnowledgeBase(organization_id=ctx.organization_id)
        ctx.db.add(kb)
        await ctx.db.flush()

    doc = Document(organization_id=ctx.organization_id, knowledge_base_id=kb.id,
                   filename=file.filename or "upload.txt", content_type=content_type)
    ctx.db.add(doc)
    await ctx.db.flush()

    storage_key = f"{ctx.organization_id}/documents/{doc.id}/{doc.filename}"
    await get_storage().put(storage_key, data)
    doc.storage_key = storage_key

    # ponytail: ingestion runs inline; enqueue to app.worker via Redis if uploads get large.
    await rag.ingest_document(ctx.db, doc, data)
    await audit(ctx, "document.uploaded", "document", doc.id, filename=doc.filename)
    await ctx.db.commit()
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, ctx: TenantCtx = Depends(require_role(Role.owner, Role.admin))):
    doc = await ctx.db.get(Document, document_id)
    if doc is None or doc.organization_id != ctx.organization_id or doc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    doc.deleted_at = utcnow()
    chunks = (await ctx.db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))).scalars().all()
    for chunk in chunks:
        chunk.deleted_at = utcnow()
    await audit(ctx, "document.deleted", "document", doc.id)
    await ctx.db.commit()


@router.post("/retrieve", response_model=list[RetrievedChunk])
async def retrieve(body: RetrieveIn, ctx: TenantCtx = Depends(get_ctx)):
    return await rag.retrieve(ctx.db, ctx.organization_id, body.query, body.top_k)
