import asyncio
from datetime import datetime, timedelta, timezone
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.event import Event
from app.models.registration import Registration, RegistrationStatus
from app.services.mailer import send_reminder_email

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def process_24h_reminders(db: AsyncSession | None = None) -> int:
    """
    Finds confirmed attendees for events taking place within the next 24 hours
    who have not yet received a reminder, sends exactly one reminder, and stamps `reminder_sent_at`.
    Returns count of sent reminders.
    """
    should_close = False
    if db is None:
        db = AsyncSessionLocal()
        should_close = True

    sent_count = 0
    try:
        now = datetime.now(timezone.utc)
        target_window = now + timedelta(hours=24)

        # 1. Query events happening within next 24 hours
        events_query = (
            select(Event)
            .where(
                Event.event_date >= now,
                Event.event_date <= target_window,
            )
        )
        result = await db.execute(events_query)
        events = result.scalars().all()

        for event in events:
            # 2. Query confirmed registrations without sent reminder
            regs_query = (
                select(Registration)
                .options(selectinload(Registration.ticket))
                .where(
                    Registration.event_id == event.id,
                    Registration.status == RegistrationStatus.confirmed,
                    Registration.reminder_sent_at.is_(None),
                )
            )
            reg_result = await db.execute(regs_query)
            registrations = reg_result.scalars().all()

            for reg in registrations:
                # Stamp reminder_sent_at first to guarantee exactly-once delivery
                reg.reminder_sent_at = datetime.now(timezone.utc)
                await db.commit()

                ticket_code = reg.ticket.ticket_code if reg.ticket else "N/A"
                date_str = event.event_date.strftime("%d.%m.%Y %H:%M")

                await send_reminder_email(
                    to_email=reg.email,
                    event_title=event.title,
                    event_date_str=date_str,
                    ticket_code=ticket_code,
                )
                sent_count += 1
                logger.info(f"Sent 24h reminder to {reg.email} for event '{event.title}'")

    except Exception as e:
        logger.error(f"Error processing 24h reminders: {e}")
    finally:
        if should_close:
            await db.close()

    return sent_count


def start_scheduler():
    """Starts background periodic job."""
    if not scheduler.running:
        scheduler.add_job(
            process_24h_reminders,
            "interval",
            minutes=1,
            id="process_24h_reminders_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("[Scheduler] Started background reminder job (interval=1m)")


def stop_scheduler():
    """Stops background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped background scheduler")
