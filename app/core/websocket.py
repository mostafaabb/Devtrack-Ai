"""
WebSocket connection manager for real-time chat and notifications.
Manages active connections per business for live messaging.
"""
import json
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from app.core.config import settings

logger = logging.getLogger("devtrack.websocket")


class ConnectionManager:
    """
    Manages WebSocket connections organized by business_id.
    
    Architecture:
    - Each business has its own connection pool
    - Staff members connect and receive real-time updates
    - Supports broadcasting to all staff in a business
    - Supports targeted messages to specific users
    """

    def __init__(self):
        # business_id -> {user_id -> WebSocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Track connection metadata
        self.connection_info: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, business_id: str, user_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        if business_id not in self.active_connections:
            self.active_connections[business_id] = {}
        
        self.active_connections[business_id][user_id] = websocket
        self.connection_info[user_id] = {
            "business_id": business_id,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"WebSocket connected: user={user_id} business={business_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "user_id": user_id,
            "business_id": business_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def disconnect(self, business_id: str, user_id: str):
        """Remove a WebSocket connection."""
        if business_id in self.active_connections:
            self.active_connections[business_id].pop(user_id, None)
            if not self.active_connections[business_id]:
                del self.active_connections[business_id]

        self.connection_info.pop(user_id, None)
        logger.info(f"WebSocket disconnected: user={user_id} business={business_id}")

    async def broadcast_to_business(self, business_id: str, message: dict):
        """Send a message to all connected users in a business."""
        if business_id not in self.active_connections:
            return

        disconnected = []
        for user_id, websocket in self.active_connections[business_id].items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(user_id)

        # Clean up broken connections
        for user_id in disconnected:
            self.disconnect(business_id, user_id)

    async def send_to_user(self, business_id: str, user_id: str, message: dict):
        """Send a message to a specific connected user."""
        if business_id in self.active_connections:
            websocket = self.active_connections[business_id].get(user_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception:
                    self.disconnect(business_id, user_id)

    def get_connected_users(self, business_id: str) -> List[str]:
        """Get list of connected user IDs for a business."""
        if business_id in self.active_connections:
            return list(self.active_connections[business_id].keys())
        return []

    def get_stats(self) -> dict:
        """Get connection statistics."""
        total = sum(len(conns) for conns in self.active_connections.values())
        return {
            "total_connections": total,
            "businesses_connected": len(self.active_connections),
        }


# Global WebSocket manager instance
ws_manager = ConnectionManager()


def authenticate_websocket(token: str) -> Optional[dict]:
    """
    Authenticate a WebSocket connection using JWT token.
    
    Returns:
        User info dict if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return {
            "user_id": payload.get("sub"),
            "business_id": payload.get("business_id"),
            "role": payload.get("role"),
            "email": payload.get("email"),
        }
    except JWTError:
        return None
