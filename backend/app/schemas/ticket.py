import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TicketRead(BaseModel):
    id: uuid.UUID
    ticket_code: str
    is_checked_in: bool
    checked_in_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
