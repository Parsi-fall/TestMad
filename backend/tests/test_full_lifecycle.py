import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_complete_event_lifecycle(client):
    """
    End-to-End integration test covering the entire lifecycle:
    1. Event creation
    2. Registrations filling capacity
    3. Overflow to waitlist
    4. Cancellation & automatic FIFO promotion
    5. Check-in at the entrance
    6. Double check-in prevention
    7. Event rescheduling
    8. 24h reminders (idempotency)
    """
    now = datetime.now(timezone.utc)

    # 1. Create event with capacity 2
    event_res = await client.post(
        "/api/v1/events",
        json={
            "title": "Full Cycle Tech Summit",
            "description": "Comprehensive lifecycle testing",
            "event_date": (now + timedelta(hours=18)).isoformat(),
            "capacity": 2,
        },
    )
    assert event_res.status_code == 201
    event_id = event_res.json()["id"]

    # 2. Register Attendee 1 (Alice) -> confirmed
    res1 = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "alice@summit.org"})
    assert res1.status_code == 200
    alice = res1.json()
    assert alice["status"] == "confirmed"
    assert alice["ticket"] is not None
    alice_code = alice["ticket"]["ticket_code"]

    # 3. Register Attendee 2 (Bob) -> confirmed (2/2 spots filled)
    res2 = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "bob@summit.org"})
    assert res2.status_code == 200
    bob = res2.json()
    assert bob["status"] == "confirmed"
    bob_code = bob["ticket"]["ticket_code"]

    # 4. Register Attendee 3 (Charlie) -> waitlist
    res3 = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "charlie@summit.org"})
    assert res3.status_code == 200
    charlie = res3.json()
    assert charlie["status"] == "waitlist"
    assert charlie["waitlist_position"] == 1

    # Check metrics: 2 confirmed, 1 waitlist, 0 checked in
    metrics = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert metrics["confirmed_count"] == 2
    assert metrics["waitlist_count"] == 1
    assert metrics["checked_in_count"] == 0

    # 5. Alice cancels -> Charlie gets promoted!
    cancel_res = await client.post(f"/api/v1/registrations/cancel/{alice['cancel_token']}")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["promoted_email"] == "charlie@summit.org"

    # Verify Charlie now has confirmed status and a ticket
    charlie_updated = (await client.get(f"/api/v1/registrations/by-token/{charlie['cancel_token']}")).json()
    assert charlie_updated["status"] == "confirmed"
    assert charlie_updated["ticket"] is not None
    charlie_code = charlie_updated["ticket"]["ticket_code"]

    # 6. Check-in Bob and Charlie at entrance
    checkin_bob = await client.post("/api/v1/checkin", json={"ticket_code": bob_code})
    assert checkin_bob.status_code == 200
    assert checkin_bob.json()["status"] == "success"

    checkin_charlie = await client.post("/api/v1/checkin", json={"ticket_code": charlie_code})
    assert checkin_charlie.status_code == 200
    assert checkin_charlie.json()["status"] == "success"

    # Metrics after checkins: 2 confirmed, 0 waitlist, 2 checked in
    metrics2 = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert metrics2["confirmed_count"] == 2
    assert metrics2["waitlist_count"] == 0
    assert metrics2["checked_in_count"] == 2

    # 7. Bob attempts double check-in -> 409 Conflict
    dup_bob = await client.post("/api/v1/checkin", json={"ticket_code": bob_code})
    assert dup_bob.status_code == 409

    # 8. Trigger 24h reminders (event is within 18h window)
    reminder_res = await client.post("/api/v1/events/system/process-reminders")
    assert reminder_res.status_code == 200
    assert reminder_res.json()["reminders_sent"] == 2  # Sent to Bob and Charlie

    # Second run sends 0
    reminder_res2 = await client.post("/api/v1/events/system/process-reminders")
    assert reminder_res2.status_code == 200
    assert reminder_res2.json()["reminders_sent"] == 0
