from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.checkin import CheckInRequest, CheckInResponse
from app.services.checkin import checkin_ticket_by_code

router = APIRouter(prefix="/checkin", tags=["Check-in"])


@router.post("", response_model=CheckInResponse)
async def checkin_ticket(
    payload: CheckInRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Check-in an attendee by ticket code.
    Enforces single-use check-in (returns 409 if already checked-in).
    Broadcasts live counter update to all connected organizer tabs.
    """
    result = await checkin_ticket_by_code(db, payload.ticket_code)
    return CheckInResponse(**result)
