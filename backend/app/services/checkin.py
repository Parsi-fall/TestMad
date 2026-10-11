from datetime import datetime, timezone
import logging
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.registration import Registration, RegistrationStatus
from app.models.ticket import Ticket
from app.services.registration import broadcast_event_stats

logger = logging.getLogger(__name__)


async def checkin_ticket_by_code(
    db: AsyncSession,
    raw_code: str,
) -> dict:
    """
    Validates and performs check-in for a ticket.
    Guarantees single-use check-in and broadcasts live stats.
    """
    code = raw_code.strip().upper()

    ticket = await db.scalar(
        select(Ticket)
        .options(
            selectinload(Ticket.registration).selectinload(Registration.event)
        )
        .where(Ticket.ticket_code == code)
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Билет с кодом «{code}» не найден",
        )

    if ticket.registration.status != RegistrationStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Билет недействителен (статус регистрации: {ticket.registration.status})",
        )

    if ticket.is_checked_in:
        time_str = (
            ticket.checked_in_at.strftime("%H:%M:%S")
            if ticket.checked_in_at
            else "ранее"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Билет «{code}» уже был использован (чекин выполнен в {time_str})",
        )

    # Perform atomic check-in
    now = datetime.now(timezone.utc)
    ticket.is_checked_in = True
    ticket.checked_in_at = now
    await db.commit()

    event = ticket.registration.event
    event_id = ticket.registration.event_id

    # Broadcast live update to all connected organizer dashboards
    await broadcast_event_stats(db, event_id)

    return {
        "status": "success",
        "message": f"Чекин успешно выполнен для {ticket.registration.email}",
        "ticket_code": ticket.ticket_code,
        "attendee_email": ticket.registration.email,
        "event_title": event.title if event else "",
        "checked_in_at": now,
    }
