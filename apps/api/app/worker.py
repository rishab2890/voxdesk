"""Background worker: consumes document-ingestion jobs from a Redis list.
Uploads currently ingest inline (see routers/documents.py); push
{"document_id": ...} onto `voxdesk:ingest` to offload heavy files here."""

import asyncio
import json
import logging

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Document
from app.providers.registry import get_storage
from app.redis_client import get_redis
from app.services import rag

log = logging.getLogger("worker")
QUEUE = "voxdesk:ingest"


async def process_job(payload: dict) -> None:
    async with SessionLocal() as db:
        doc = (
            await db.execute(select(Document).where(Document.id == payload["document_id"]))
        ).scalar_one_or_none()
        if doc is None:
            log.warning("Unknown document %s", payload)
            return
        data = await get_storage().get(doc.storage_key)
        await rag.ingest_document(db, doc, data)
        await db.commit()
        log.info("Ingested %s (%d chunks)", doc.filename, doc.chunk_count)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    log.info("Worker started, polling %s", QUEUE)
    while True:
        r = get_redis()
        try:
            item = await r.blpop(QUEUE, timeout=5) if r else None
        except Exception:
            log.warning("Redis unavailable, retrying in 5s")
            await asyncio.sleep(5)
            continue
        if item is None:
            continue
        try:
            await process_job(json.loads(item[1]))
        except Exception:
            log.exception("Job failed: %s", item[1])


if __name__ == "__main__":
    asyncio.run(main())
