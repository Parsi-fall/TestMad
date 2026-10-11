import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_checkin_flow(client):
    # 1. Create an event
    event_res = await client.post(
        "/api/v1/events",
        json={
            "title": "Check-in Demo Event",
            "description": "Testing ticket entry and duplicate rejection",
            "event_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "capacity": 5,
        },
    )
    assert event_res.status_code == 201
    event_id = event_res.json()["id"]

    # 2. Register attendee
    reg_res = await client.post(
        f"/api/v1/events/{event_id}/register",
        json={"email": "visitor@example.com"},
    )
    assert reg_res.status_code == 200
    ticket_code = reg_res.json()["ticket"]["ticket_code"]

    # 3. Before check-in: checked_in_count should be 0
    stats_before = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert stats_before["checked_in_count"] == 0

    # 4. First check-in attempt (with lowercase and whitespace to verify sanitization)
    checkin_res = await client.post(
        "/api/v1/checkin",
        json={"ticket_code": f"  {ticket_code.lower()}  "},
    )
    assert checkin_res.status_code == 200
    data = checkin_res.json()
    assert data["status"] == "success"
    assert data["ticket_code"] == ticket_code
    assert data["attendee_email"] == "visitor@example.com"

    # 5. After check-in: checked_in_count should be 1
    stats_after = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert stats_after["checked_in_count"] == 1

    # 6. Second check-in attempt with SAME code -> must fail with 409 Conflict
    dup_res = await client.post(
        "/api/v1/checkin",
        json={"ticket_code": ticket_code},
    )
    assert dup_res.status_code == 409
    assert "уже был использован" in dup_res.json()["detail"]

    # Checked-in counter must remain 1
    stats_final = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert stats_final["checked_in_count"] == 1

    # 7. Non-existent ticket code -> 404 Not Found
    not_found_res = await client.post(
        "/api/v1/checkin",
        json={"ticket_code": "TKT-NONEXISTENT"},
    )
    assert not_found_res.status_code == 404
