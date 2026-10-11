import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.types import Uuid as GenericUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.registration import Registration


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    registration_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid,
        ForeignKey("registrations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    ticket_code: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        index=True,
        nullable=False,
    )
    is_checked_in: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    registration: Mapped["Registration"] = relationship(
        "Registration",
        back_populates="ticket",
        lazy="selectin",
    )
