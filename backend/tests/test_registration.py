import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_registration_and_idempotency(client):
    # 1. Create an event with capacity = 2
    event_payload = {
        "title": "Test Concurrency Meetup",
        "description": "Testing spot limits and duplicate emails",
        "event_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        "capacity": 2,
    }
    create_res = await client.post("/api/v1/events", json=event_payload)
    assert create_res.status_code == 201
    event_id = create_res.json()["id"]

    # 2. Register first participant
    reg1 = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "alice@example.com"})
    assert reg1.status_code == 200
    data1 = reg1.json()
    assert data1["status"] == "confirmed"
    assert data1["ticket"] is not None
    ticket_code1 = data1["ticket"]["ticket_code"]
    assert ticket_code1.startswith("TKT-")

    # 3. Duplicate registration with same email (alice@example.com)
    dup = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "alice@example.com"})
    assert dup.status_code == 200
    dup_data = dup.json()
    assert dup_data["status"] == "confirmed"
    assert dup_data["ticket"]["ticket_code"] == ticket_code1  # Same ticket!
    assert dup_data["id"] == data1["id"]

    # 4. Register second participant (fills remaining spot: 2/2)
    reg2 = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "bob@example.com"})
    assert reg2.status_code == 200
    assert reg2.json()["status"] == "confirmed"

    # 5. Register third participant (capacity full -> waitlist)
    reg3 = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "charlie@example.com"})
    assert reg3.status_code == 200
    data3 = reg3.json()
    assert data3["status"] == "waitlist"
    assert data3["ticket"] is None
    assert data3["waitlist_position"] == 1

    # 6. Check event counters
    event_check = await client.get(f"/api/v1/events/{event_id}")
    assert event_check.status_code == 200
    stats = event_check.json()
    assert stats["confirmed_count"] == 2
    assert stats["waitlist_count"] == 1
