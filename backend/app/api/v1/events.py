import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.event import Event
from app.schemas.event import EventCreate, EventRead
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
