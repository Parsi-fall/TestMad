import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.event import Event
from app.schemas.event import EventCreate, EventRead, EventRescheduleRequest
from app.services.registration import get_event_stats

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=List[EventRead])
async def list_events(db: AsyncSession = Depends(get_db)):
    """List all events with their live registration metrics."""
    result = await db.execute(select(Event).order_by(Event.event_date.asc()))
    events = result.scalars().all()

    output = []
    for event in events:
        stats = await get_event_stats(db, event.id)
        event_dict = {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "event_date": event.event_date,
            "capacity": event.capacity,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
            "confirmed_count": stats["confirmed_count"],
            "waitlist_count": stats["waitlist_count"],
            "checked_in_count": stats["checked_in_count"],
        }
        output.append(EventRead(**event_dict))
    return output


@router.get("/{event_id}", response_model=EventRead)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get single event details with metrics."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Событие с ID {event_id} не найдено",
        )

    stats = await get_event_stats(db, event_id)
    return EventRead(
        id=event.id,
        title=event.title,
        description=event.description,
        event_date=event.event_date,
        capacity=event.capacity,
        created_at=event.created_at,
        updated_at=event.updated_at,
        confirmed_count=stats["confirmed_count"],
        waitlist_count=stats["waitlist_count"],
        checked_in_count=stats["checked_in_count"],
    )


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate, db: AsyncSession = Depends(get_db)):
    """Create a new event."""
    new_event = Event(
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        capacity=payload.capacity,
    )
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    return EventRead(
        id=new_event.id,
        title=new_event.title,
        description=new_event.description,
        event_date=new_event.event_date,
        capacity=new_event.capacity,
        created_at=new_event.created_at,
        updated_at=new_event.updated_at,
        confirmed_count=0,
        waitlist_count=0,
        checked_in_count=0,
    )


@router.post("/{event_id}/reschedule", response_model=EventRead)
async def reschedule_event(
    event_id: uuid.UUID,
    payload: EventRescheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reschedules an event to a new date and notifies all registered attendees via email.
    """
    from sqlalchemy.orm import selectinload
    from app.models.registration import Registration, RegistrationStatus
    from app.services.mailer import send_reschedule_email
    from app.services.registration import broadcast_event_stats

    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Событие с ID {event_id} не найдено",
        )

    old_date_str = event.event_date.strftime("%d.%m.%Y %H:%M")
    new_date_str = payload.new_event_date.strftime("%d.%m.%Y %H:%M")

    # Update event date
    event.event_date = payload.new_event_date

    # Fetch all active attendees (confirmed and waitlist)
    regs_result = await db.execute(
        select(Registration)
        .options(selectinload(Registration.ticket))
        .where(
            Registration.event_id == event_id,
            Registration.status.in_([RegistrationStatus.confirmed, RegistrationStatus.waitlist]),
        )
    )
    attendees = regs_result.scalars().all()

    # Reset reminder_sent_at so new 24h reminder can be sent for the new date
    for reg in attendees:
        reg.reminder_sent_at = None

    await db.commit()
    await db.refresh(event)

    # Send reschedule emails to all participants
    for reg in attendees:
        ticket_code = reg.ticket.ticket_code if reg.ticket else None
        await send_reschedule_email(
            to_email=reg.email,
            event_title=event.title,
            new_date_str=new_date_str,
            ticket_code=ticket_code,
        )

    # Broadcast updated stats/info to organizers
    await broadcast_event_stats(db, event_id)

    stats = await get_event_stats(db, event_id)
    return EventRead(
        id=event.id,
        title=event.title,
        description=event.description,
        event_date=event.event_date,
        capacity=event.capacity,
        created_at=event.created_at,
        updated_at=event.updated_at,
        confirmed_count=stats["confirmed_count"],
        waitlist_count=stats["waitlist_count"],
        checked_in_count=stats["checked_in_count"],
    )


@router.post("/system/process-reminders", tags=["System"])
async def trigger_reminders(db: AsyncSession = Depends(get_db)):
    """Manually trigger the 24h reminder processing job."""
    from app.services.scheduler import process_24h_reminders
    sent = await process_24h_reminders(db)
    return {"status": "ok", "reminders_sent": sent}
