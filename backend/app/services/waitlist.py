import asyncio
import logging
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.registration import Registration, RegistrationStatus
from app.models.ticket import Ticket
from app.services.mailer import send_promoted_email
from app.services.notifier import manager
from app.services.registration import broadcast_event_stats
from app.utils.code_generator import generate_ticket_code

logger = logging.getLogger(__name__)
_cancel_sqlite_lock = asyncio.Lock()


async def cancel_registration_by_token(
    db: AsyncSession,
    cancel_token: str,
) -> dict:
    """
    Cancel an attendee's registration.
    If the attendee was 'confirmed', automatically promotes the first attendee from 'waitlist'
    and issues them a ticket and sends an email.
    """
    if db.bind.dialect.name == "sqlite":
        async with _cancel_sqlite_lock:
            return await _cancel_registration_impl(db, cancel_token)
    return await _cancel_registration_impl(db, cancel_token)


async def _cancel_registration_impl(
    db: AsyncSession,
    cancel_token: str,
) -> dict:
    # 1. Fetch registration by cancel_token
    reg = await db.scalar(
        select(Registration)
        .options(selectinload(Registration.ticket), selectinload(Registration.event))
        .where(Registration.cancel_token == cancel_token)
    )

    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Регистрация с указанным токеном не найдена",
        )

    if reg.status == RegistrationStatus.cancelled:
        return {
            "status": "already_cancelled",
            "message": "Регистрация уже была отменена ранее",
            "promoted_email": None,
        }

    event_id = reg.event_id
    was_confirmed = (reg.status == RegistrationStatus.confirmed)

    # 2. Lock event row to safely manage capacity
    event_query = select(Event).where(Event.id == event_id)
    if db.bind.dialect.name != "sqlite":
        event_query = event_query.with_for_update()
    event = await db.scalar(event_query)

    # 3. Mark current registration as cancelled
    reg.status = RegistrationStatus.cancelled
    if reg.ticket:
        # Delete or invalidate ticket
        await db.delete(reg.ticket)

    promoted_email = None

    # 4. If the cancelling attendee was confirmed, promote the first candidate from waitlist
    if was_confirmed:
        waitlist_query = (
            select(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.waitlist,
            )
            .order_by(Registration.created_at.asc())
            .limit(1)
        )
        if db.bind.dialect.name != "sqlite":
            waitlist_query = waitlist_query.with_for_update()
        
        promoted_reg = await db.scalar(waitlist_query)

        if promoted_reg:
            promoted_reg.status = RegistrationStatus.confirmed
            ticket_code = generate_ticket_code()
            new_ticket = Ticket(
                registration_id=promoted_reg.id,
                ticket_code=ticket_code,
            )
            db.add(new_ticket)
            promoted_email = promoted_reg.email

            await db.commit()

            # Send email to newly promoted attendee
            date_str = event.event_date.strftime("%d.%m.%Y %H:%M") if event else ""
            await send_promoted_email(
                to_email=promoted_reg.email,
                event_title=event.title if event else "Мероприятие",
                event_date_str=date_str,
                ticket_code=ticket_code,
                cancel_token=promoted_reg.cancel_token,
            )
        else:
            await db.commit()
    else:
        await db.commit()

    # 5. Broadcast live update to organizer dashboard
    await broadcast_event_stats(db, event_id)

    return {
        "status": "success",
        "message": "Участие успешно отменено",
        "promoted_email": promoted_email,
    }
