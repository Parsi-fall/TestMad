import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    title: str
    description: str | None = None
    event_date: datetime
    capacity: int = Field(gt=0, description="Лимит мест должен быть строго больше 0")


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_date: datetime | None = None
    capacity: int | None = Field(default=None, gt=0)


class EventRead(EventBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    confirmed_count: int = 0
    waitlist_count: int = 0
    checked_in_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class EventRescheduleRequest(BaseModel):
    new_event_date: datetime
