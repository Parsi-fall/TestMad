import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.event import Event


async def init_db() -> None:
    # Ensure tables are created (useful when running without alembic or on startup)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial event if database is empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).limit(1))
        existing_event = result.scalars().first()

        if not existing_event:
            demo_event = Event(
                title="AI & Python Architecture Meetup 2026",
                description="Практический митап по высоконагруженным сервисам на FastAPI и PostgreSQL.",
                event_date=datetime.now(timezone.utc) + timedelta(days=2),
                capacity=5,  # Небольшой лимит для наглядной демонстрации waitlist
            )
            session.add(demo_event)
            await session.commit()
            print(f"[init_db] Created demo event: '{demo_event.title}' with ID: {demo_event.id} (capacity: {demo_event.capacity})")
        else:
            print(f"[init_db] Database already contains event '{existing_event.title}' (ID: {existing_event.id})")


if __name__ == "__main__":
    asyncio.run(init_db())
