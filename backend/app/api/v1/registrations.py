import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.models.registration import Registration, RegistrationStatus
from app.schemas.registration import RegistrationCreate, RegistrationRead
from app.schemas.ticket import TicketRead
from app.services.registration import register_attendee

router = APIRouter(tags=["Registrations"])


@router.post("/events/{event_id}/register", response_model=RegistrationRead)
async def register(
    event_id: uuid.UUID,
    payload: RegistrationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register an attendee by email for an event.
    Guarantees concurrency safety (locking) and email idempotency.
    """
    reg, waitlist_pos, is_new = await register_attendee(db, event_id, payload.email)

    ticket_read = None
    if reg.ticket:
        ticket_read = TicketRead(
            id=reg.ticket.id,
            ticket_code=reg.ticket.ticket_code,
            is_checked_in=reg.ticket.is_checked_in,
            checked_in_at=reg.ticket.checked_in_at,
            created_at=reg.ticket.created_at,
        )

    cancel_url = f"{settings.FRONTEND_URL}/cancel?token={reg.cancel_token}"

    return RegistrationRead(
        id=reg.id,
        event_id=reg.event_id,
        email=reg.email,
        status=reg.status,
        cancel_token=reg.cancel_token,
        cancel_url=cancel_url,
        waitlist_position=waitlist_pos,
        ticket=ticket_read,
        created_at=reg.created_at,
    )


@router.get("/registrations/by-token/{cancel_token}", response_model=RegistrationRead)
async def get_registration_by_token(
    cancel_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch registration info by cancel token."""
    result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.ticket))
        .where(Registration.cancel_token == cancel_token)
    )
    reg = result.scalars().first()
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Регистрация с указанным токеном не найдена",
        )

    ticket_read = None
    if reg.ticket:
        ticket_read = TicketRead(
            id=reg.ticket.id,
            ticket_code=reg.ticket.ticket_code,
            is_checked_in=reg.ticket.is_checked_in,
            checked_in_at=reg.ticket.checked_in_at,
            created_at=reg.ticket.created_at,
        )

    cancel_url = f"{settings.FRONTEND_URL}/cancel?token={reg.cancel_token}"

    return RegistrationRead(
        id=reg.id,
        event_id=reg.event_id,
        email=reg.email,
        status=reg.status,
        cancel_token=reg.cancel_token,
        cancel_url=cancel_url,
        waitlist_position=None,
        ticket=ticket_read,
        created_at=reg.created_at,
    )
