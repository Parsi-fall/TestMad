import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_cancellation_and_auto_promotion(client):
    # 1. Create event with capacity = 1
    event_res = await client.post(
        "/api/v1/events",
        json={
            "title": "VIP Masterclass",
            "description": "Only 1 spot available",
            "event_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "capacity": 1,
        },
    )
    assert event_res.status_code == 201
    event_id = event_res.json()["id"]

    # 2. User A registers -> confirmed
    res_a = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "usera@example.com"})
    user_a = res_a.json()
    assert user_a["status"] == "confirmed"
    assert user_a["ticket"] is not None

    # 3. User B registers -> waitlist (pos 1)
    res_b = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "userb@example.com"})
    user_b = res_b.json()
    assert user_b["status"] == "waitlist"

    # 4. User C registers -> waitlist (pos 2)
    res_c = await client.post(f"/api/v1/events/{event_id}/register", json={"email": "userc@example.com"})
    user_c = res_c.json()
    assert user_c["status"] == "waitlist"

    # 5. Check counters: 1 confirmed, 2 waitlist
    stats = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert stats["confirmed_count"] == 1
    assert stats["waitlist_count"] == 2

    # 6. User A cancels registration
    cancel_res = await client.post(f"/api/v1/registrations/cancel/{user_a['cancel_token']}")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "success"
    # User B should be promoted!
    assert cancel_data["promoted_email"] == "userb@example.com"

    # 7. Verify User B is now confirmed and received a ticket
    b_updated = (await client.get(f"/api/v1/registrations/by-token/{user_b['cancel_token']}")).json()
    assert b_updated["status"] == "confirmed"
    assert b_updated["ticket"] is not None
    assert b_updated["ticket"]["ticket_code"].startswith("TKT-")

    # 8. Verify User C is still in waitlist
    c_updated = (await client.get(f"/api/v1/registrations/by-token/{user_c['cancel_token']}")).json()
    assert c_updated["status"] == "waitlist"

    # 9. Counters: 1 confirmed (User B), 1 waitlist (User C)
    stats2 = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert stats2["confirmed_count"] == 1
    assert stats2["waitlist_count"] == 1

    # 10. Repeat cancel for User A -> already_cancelled
    repeat_cancel = await client.post(f"/api/v1/registrations/cancel/{user_a['cancel_token']}")
    assert repeat_cancel.status_code == 200
    assert repeat_cancel.json()["status"] == "already_cancelled"
