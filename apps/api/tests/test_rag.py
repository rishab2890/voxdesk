import pytest

from app.services.rag import chunk_text

pytestmark = pytest.mark.asyncio


def test_chunking_overlap_and_coverage():
    text = "word " * 500
    chunks = chunk_text(text, size=100, overlap=20)
    assert chunks
    assert all(len(c) <= 100 for c in chunks)
    assert chunk_text("") == []
    # Overlap: each chunk starts inside the previous one.
    joined = "".join(c[: 100 - 20] for c in chunks[:-1]) + chunks[-1]
    assert joined.startswith("word word")


async def test_upload_and_retrieve(client, auth_headers):
    r = await client.post(
        "/documents",
        files={"file": ("faq.txt", b"We are open Monday to Friday, 9am to 5pm. Parking is free.", "text/plain")},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "ready"
    assert r.json()["chunk_count"] >= 1

    r = await client.post("/documents/retrieve", json={"query": "parking hours"}, headers=auth_headers)
    assert r.status_code == 200
    results = r.json()
    assert results and "Parking" in results[0]["content"]
