import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_24h_reminder_exactly_once(client):
    now = datetime.now(timezone.utc)

    # 1. Create an event occurring in 10 hours (within the 24h window)
    event_res = await client.post(
        "/api/v1/events",
        json={
            "title": "Tomorrow Morning Keynote",
            "description": "Event starting in 10 hours",
            "event_date": (now + timedelta(hours=10)).isoformat(),
            "capacity": 5,
        },
    )
    assert event_res.status_code == 201
    event_id = event_res.json()["id"]

    # 2. Register 2 attendees
    await client.post(f"/api/v1/events/{event_id}/register", json={"email": "early1@example.com"})
    await client.post(f"/api/v1/events/{event_id}/register", json={"email": "early2@example.com"})

    # 3. Process reminders for the first time -> exactly 2 sent
    first_run = await client.post("/api/v1/events/system/process-reminders")
    assert first_run.status_code == 200
    assert first_run.json()["reminders_sent"] == 2

    # 4. Process reminders for the second time -> exactly 0 sent (idempotency guarantee)
    second_run = await client.post("/api/v1/events/system/process-reminders")
    assert second_run.status_code == 200
    assert second_run.json()["reminders_sent"] == 0


@pytest.mark.asyncio
async def test_reschedule_event_and_notification(client):
    now = datetime.now(timezone.utc)
    initial_date = now + timedelta(days=2)
    new_date = now + timedelta(days=5)

    # 1. Create event
    event_res = await client.post(
        "/api/v1/events",
        json={
            "title": "Flexible Schedule Conference",
            "description": "Date may change",
            "event_date": initial_date.isoformat(),
            "capacity": 3,
        },
    )
    assert event_res.status_code == 201
    event_id = event_res.json()["id"]

    # 2. Register attendee
    reg_res = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "conf_guest@example.com"})
    assert reg_res.status_code == 200

    # 3. Reschedule event
    reschedule_res = await client.post(
        f"/api/v1/events/{event_id}/reschedule",
        json={"new_event_date": new_date.isoformat()},
    )
    assert reschedule_res.status_code == 200
    updated_event = reschedule_res.json()
    parsed_updated_date = datetime.fromisoformat(updated_event["event_date"]).replace(tzinfo=timezone.utc)
    assert abs((parsed_updated_date - new_date).total_seconds()) < 2
