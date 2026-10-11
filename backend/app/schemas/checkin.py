from datetime import datetime
from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    ticket_code: str = Field(..., min_length=3, max_length=32, description="Код билета, например TKT-7X9K2P")


class CheckInResponse(BaseModel):
    status: str
    message: str
    ticket_code: str
    attendee_email: str
    event_title: str
    checked_in_at: datetime
