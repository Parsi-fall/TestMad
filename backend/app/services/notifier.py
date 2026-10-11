import logging
import uuid
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Maps event_id -> list of active WebSockets
        self.active_connections: Dict[uuid.UUID, List[WebSocket]] = {}

    async def connect(self, event_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id] = []
        self.active_connections[event_id].append(websocket)
        logger.info(f"WebSocket client connected to event {event_id}. Total: {len(self.active_connections[event_id])}")

    def disconnect(self, event_id: uuid.UUID, websocket: WebSocket):
        if event_id in self.active_connections:
            if websocket in self.active_connections[event_id]:
                self.active_connections[event_id].remove(websocket)
            if not self.active_connections[event_id]:
                del self.active_connections[event_id]
        logger.info(f"WebSocket client disconnected from event {event_id}")

    async def broadcast(self, event_id: uuid.UUID, data: dict):
        if event_id not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[event_id]:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(event_id, dead)


manager = ConnectionManager()
