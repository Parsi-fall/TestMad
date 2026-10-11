import enum
import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    String,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.types import Uuid as GenericUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.ticket import Ticket


def generate_cancel_token() -> str:
    return secrets.token_urlsafe(32)


class RegistrationStatus(str, enum.Enum):
    confirmed = "confirmed"
    waitlist = "waitlist"
    cancelled = "cancelled"


class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RegistrationStatus] = mapped_column(
        SQLEnum(RegistrationStatus, name="registration_status", native_enum=False),
        default=RegistrationStatus.confirmed,
        nullable=False,
    )
    cancel_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        default=generate_cancel_token,
        nullable=False,
    )
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship("Event", back_populates="registrations")
    ticket: Mapped["Ticket | None"] = relationship(
        "Ticket",
        back_populates="registration",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("event_id", "email", name="uq_registrations_event_email"),
        Index("ix_registrations_event_status_created", "event_id", "status", "created_at"),
    )
