import logging
import uuid
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.notifier import manager
from app.services.registration import get_event_stats

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/events/{event_id}")
async def websocket_event_metrics(
    websocket: WebSocket,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket channel for real-time organizer dashboard statistics.
    Immediately pushes current counters upon connection, then streams live updates.
    """
    await manager.connect(event_id, websocket)

    # Immediately send current counts upon connection
    try:
        stats = await get_event_stats(db, event_id)
        await websocket.send_json(stats)
    except Exception as e:
        logger.warning(f"Failed to send initial stats over websocket: {e}")

    try:
        while True:
            # Keep connection open and respond to client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(event_id, websocket)
    except Exception as e:
        logger.info(f"WebSocket closed: {e}")
        manager.disconnect(event_id, websocket)
