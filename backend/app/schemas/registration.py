import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.registration import RegistrationStatus
from app.schemas.ticket import TicketRead


class RegistrationCreate(BaseModel):
    email: EmailStr


class RegistrationRead(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    email: str
    status: RegistrationStatus
    cancel_token: str
    cancel_url: str | None = None
    waitlist_position: int | None = None
    ticket: TicketRead | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegistrationCancelResponse(BaseModel):
    status: str
    message: str
    promoted_email: str | None = None
