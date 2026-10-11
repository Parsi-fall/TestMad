import uuid
from datetime import timezone
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.registration import Registration, RegistrationStatus
from app.models.ticket import Ticket
from app.services.mailer import send_ticket_email, send_waitlist_email
from app.services.notifier import manager
from app.utils.code_generator import generate_ticket_code


async def get_event_stats(db: AsyncSession, event_id: uuid.UUID) -> dict:
    """Calculate counts for confirmed, waitlist, and checked-in attendees."""
    confirmed_count = await db.scalar(
        select(func.count(Registration.id)).where(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.confirmed,
        )
    ) or 0

    waitlist_count = await db.scalar(
        select(func.count(Registration.id)).where(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.waitlist,
        )
    ) or 0

    checked_in_count = await db.scalar(
        select(func.count(Ticket.id))
        .join(Registration, Ticket.registration_id == Registration.id)
        .where(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.confirmed,
            Ticket.is_checked_in.is_(True),
        )
    ) or 0

    return {
        "event_id": str(event_id),
        "confirmed_count": confirmed_count,
        "waitlist_count": waitlist_count,
        "checked_in_count": checked_in_count,
    }


async def broadcast_event_stats(db: AsyncSession, event_id: uuid.UUID):
    stats = await get_event_stats(db, event_id)
    await manager.broadcast(event_id, stats)


import asyncio
_sqlite_lock = asyncio.Lock()


async def register_attendee(
    db: AsyncSession,
    event_id: uuid.UUID,
    email: str,
) -> tuple[Registration, int | None, bool]:
    if db.bind.dialect.name == "sqlite":
        async with _sqlite_lock:
            return await _register_attendee_impl(db, event_id, email)
    return await _register_attendee_impl(db, event_id, email)


async def _register_attendee_impl(
    db: AsyncSession,
    event_id: uuid.UUID,
    email: str,
) -> tuple[Registration, int | None, bool]:
    email = email.strip().lower()

    # 1. Lock the event row to serialize concurrent registrations for this event (on Postgres)
    event_query = select(Event).where(Event.id == event_id)
    if db.bind.dialect.name != "sqlite":
        event_query = event_query.with_for_update()
    event = await db.scalar(event_query)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Событие с ID {event_id} не найдено",
        )

    # 2. Check if a registration already exists for this email
    existing_reg = await db.scalar(
        select(Registration)
        .options(selectinload(Registration.ticket))
        .where(
            Registration.event_id == event_id,
            Registration.email == email,
        )
    )

    date_str = event.event_date.strftime("%d.%m.%Y %H:%M")

    if existing_reg:
        # Idempotency handling
        if existing_reg.status == RegistrationStatus.confirmed:
            if existing_reg.ticket:
                await send_ticket_email(
                    to_email=existing_reg.email,
                    event_title=event.title,
                    event_date_str=date_str,
                    ticket_code=existing_reg.ticket.ticket_code,
                    cancel_token=existing_reg.cancel_token,
                )
            return existing_reg, None, False

        elif existing_reg.status == RegistrationStatus.waitlist:
            # Calculate current waitlist position
            pos = await db.scalar(
                select(func.count(Registration.id)).where(
                    Registration.event_id == event_id,
                    Registration.status == RegistrationStatus.waitlist,
                    Registration.created_at <= existing_reg.created_at,
                )
            ) or 1
            return existing_reg, pos, False

        elif existing_reg.status == RegistrationStatus.cancelled:
            # Reactivate cancelled registration
            confirmed_count = await db.scalar(
                select(func.count(Registration.id)).where(
                    Registration.event_id == event_id,
                    Registration.status == RegistrationStatus.confirmed,
                )
            ) or 0

            if confirmed_count < event.capacity:
                existing_reg.status = RegistrationStatus.confirmed
                if not existing_reg.ticket:
                    ticket_code = generate_ticket_code()
                    ticket = Ticket(
                        registration_id=existing_reg.id,
                        ticket_code=ticket_code,
                    )
                    db.add(ticket)
                    existing_reg.ticket = ticket
                await db.commit()
                await db.refresh(existing_reg)
                await send_ticket_email(
                    to_email=existing_reg.email,
                    event_title=event.title,
                    event_date_str=date_str,
                    ticket_code=existing_reg.ticket.ticket_code,
                    cancel_token=existing_reg.cancel_token,
                )
                await broadcast_event_stats(db, event_id)
                return existing_reg, None, True
            else:
                existing_reg.status = RegistrationStatus.waitlist
                await db.commit()
                await db.refresh(existing_reg)
                pos = await db.scalar(
                    select(func.count(Registration.id)).where(
                        Registration.event_id == event_id,
                        Registration.status == RegistrationStatus.waitlist,
                    )
                ) or 1
                await send_waitlist_email(
                    to_email=existing_reg.email,
                    event_title=event.title,
                    event_date_str=date_str,
                    position=pos,
                    cancel_token=existing_reg.cancel_token,
                )
                await broadcast_event_stats(db, event_id)
                return existing_reg, pos, True

    # 3. New registration: Check current confirmed count against capacity
    confirmed_count = await db.scalar(
        select(func.count(Registration.id)).where(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.confirmed,
        )
    ) or 0

    if confirmed_count < event.capacity:
        # User gets a confirmed spot!
        new_reg = Registration(
            event_id=event_id,
            email=email,
            status=RegistrationStatus.confirmed,
        )
        db.add(new_reg)
        await db.flush()  # Generate ID for new_reg

        ticket_code = generate_ticket_code()
        ticket = Ticket(
            registration_id=new_reg.id,
            ticket_code=ticket_code,
        )
        db.add(ticket)
        await db.commit()

        # Eager load ticket
        await db.refresh(new_reg)
        loaded_reg = await db.scalar(
            select(Registration)
            .options(selectinload(Registration.ticket))
            .where(Registration.id == new_reg.id)
        ) or new_reg

        # Send ticket email via MailHog
        await send_ticket_email(
            to_email=email,
            event_title=event.title,
            event_date_str=date_str,
            ticket_code=ticket_code,
            cancel_token=loaded_reg.cancel_token,
        )

        await broadcast_event_stats(db, event_id)
        return loaded_reg, None, True

    else:
        # Capacity reached: Place attendee into waitlist
        new_reg = Registration(
            event_id=event_id,
            email=email,
            status=RegistrationStatus.waitlist,
        )
        db.add(new_reg)
        await db.commit()
        await db.refresh(new_reg)

        # Calculate position in waitlist
        pos = await db.scalar(
            select(func.count(Registration.id)).where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.waitlist,
                Registration.created_at <= new_reg.created_at,
            )
        ) or 1

        # Send waitlist email
        await send_waitlist_email(
            to_email=email,
            event_title=event.title,
            event_date_str=date_str,
            position=pos,
            cancel_token=new_reg.cancel_token,
        )

        await broadcast_event_stats(db, event_id)
        return new_reg, pos, True
