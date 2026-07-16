import pytest

pytestmark = pytest.mark.asyncio


async def _make_agent(client, headers, **overrides):
    body = {"name": "Receptionist", "transfer_number": "+15559990000", **overrides}
    r = await client.post("/agents", json=body, headers=headers)
    return r.json()["id"]


async def test_simulated_call_books_appointment(client, auth_headers):
    agent_id = await _make_agent(client, auth_headers)
    r = await client.post("/calls/simulate", json={
        "agent_id": agent_id,
        "utterances": ["Hi, I'd like to book an appointment for tomorrow"],
    }, headers=auth_headers)
    assert r.status_code == 201, r.text
    call = r.json()
    assert call["status"] == "completed"
    assert call["summary"] is not None
    roles = [t["role"] for t in call["turns"]]
    assert roles[0] == "agent" and "caller" in roles

    r = await client.get("/appointments", headers=auth_headers)
    assert len(r.json()) == 1


async def test_collect_caller_name_and_recording(client, auth_headers):
    agent_id = await _make_agent(client, auth_headers)
    r = await client.post("/calls/simulate", json={
        "agent_id": agent_id,
        "utterances": ["Hi, my name is Jane Smith and I'd like to book an appointment"],
    }, headers=auth_headers)
    call = r.json()
    assert call["caller_name"] == "Jane Smith"
    assert call["has_recording"] is True

    r = await client.get("/appointments", headers=auth_headers)
    assert r.json()[0]["contact_name"] == "Jane Smith"

    r = await client.get(f"/calls/{call['id']}/recording", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content[:4] == b"RIFF"


async def test_transfer_after_booking_handoff(client, auth_headers):
    agent_id = await _make_agent(client, auth_headers, transfer_after_booking=True)
    r = await client.post("/calls/simulate", json={
        "agent_id": agent_id,
        "utterances": ["I want to schedule an appointment please"],
    }, headers=auth_headers)
    call = r.json()
    assert call["status"] == "transferred"
    assert call["transferred_to"] == "+15559990000"
    # Caller was told about the hand-off after booking.
    assert "team member" in call["turns"][-1]["content"]
    r = await client.get("/appointments", headers=auth_headers)
    assert len(r.json()) == 1


async def test_simulated_call_transfers_to_human(client, auth_headers):
    agent_id = await _make_agent(client, auth_headers)
    r = await client.post("/calls/simulate", json={
        "agent_id": agent_id,
        "utterances": ["I want to speak to a human please", "this should not run"],
    }, headers=auth_headers)
    call = r.json()
    assert call["status"] == "transferred"
    assert call["transferred_to"] == "+15559990000"

    r = await client.get("/analytics", headers=auth_headers)
    stats = r.json()
    assert stats["total_calls"] == 1
    assert stats["transferred_calls"] == 1
