import asyncio
import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_concurrent_registration_for_last_spot(client):
    # 1. Create an event with capacity = 1
    event_payload = {
        "title": "Strict 1-Spot Highlander Meetup",
        "description": "There can be only one confirmed attendee",
        "event_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "capacity": 1,
    }
    create_res = await client.post("/api/v1/events", json=event_payload)
    assert create_res.status_code == 201
    event_id = create_res.json()["id"]

    # 2. Fire 5 simultaneous registration requests
    emails = [f"racer_{i}@example.com" for i in range(5)]
    tasks = [
        client.post(f"/api/v1/events/{event_id}/register", json={"email": email})
        for email in emails
    ]
    responses = await asyncio.gather(*tasks)

    # All requests must return HTTP 200 without throwing 500 errors
    for r in responses:
        assert r.status_code == 200

    results = [r.json() for r in responses]
    confirmed = [res for res in results if res["status"] == "confirmed"]
    waitlisted = [res for res in results if res["status"] == "waitlist"]

    # Verify: Exactly 1 got the confirmed spot, exactly 4 went to waitlist
    assert len(confirmed) == 1
    assert len(waitlisted) == 4
    assert confirmed[0]["ticket"] is not None

    # Check database counters via API
    event_check = await client.get(f"/api/v1/events/{event_id}")
    stats = event_check.json()
    assert stats["confirmed_count"] == 1
    assert stats["waitlist_count"] == 4
