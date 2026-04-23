"""
WebSocket API routes for real-time communication.
Handles live chat updates, notifications, and status changes.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, timezone
import json
import logging

from app.core.websocket import ws_manager, authenticate_websocket

logger = logging.getLogger("devtrack.ws_routes")

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Main WebSocket endpoint for real-time updates.
    
    Connect with: ws://host/ws?token=YOUR_JWT_TOKEN
    
    Message types:
    - new_message: New chat message received
    - conversation_update: Conversation status changed
    - order_update: Order status changed
    - booking_update: Booking status changed
    - notification: Generic notification
    - typing: User is typing indicator
    - ping/pong: Keep-alive
    """
    # Authenticate the WebSocket connection
    user = authenticate_websocket(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    user_id = user["user_id"]
    business_id = user["business_id"]

    await ws_manager.connect(websocket, business_id, user_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    # Keep-alive pong
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                elif msg_type == "typing":
                    # Broadcast typing indicator to other users in the business
                    await ws_manager.broadcast_to_business(business_id, {
                        "type": "typing",
                        "user_id": user_id,
                        "conversation_id": message.get("conversation_id"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                elif msg_type == "read_receipt":
                    # Mark messages as read
                    await ws_manager.broadcast_to_business(business_id, {
                        "type": "read_receipt",
                        "user_id": user_id,
                        "conversation_id": message.get("conversation_id"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                elif msg_type == "status_update":
                    # Broadcast status change (e.g., going online/offline)
                    await ws_manager.broadcast_to_business(business_id, {
                        "type": "user_status",
                        "user_id": user_id,
                        "status": message.get("status", "online"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                else:
                    logger.debug(f"Unknown WS message type: {msg_type}")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(business_id, user_id)
        # Notify other users
        await ws_manager.broadcast_to_business(business_id, {
            "type": "user_disconnected",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


@router.websocket("/ws/widget/{business_slug}")
async def widget_websocket(
    websocket: WebSocket,
    business_slug: str,
):
    """
    WebSocket endpoint for the public chat widget.
    No authentication required — uses business_slug as identifier.
    """
    await websocket.accept()
    
    # Generate a temporary session ID for this widget connection
    import uuid
    session_id = str(uuid.uuid4())[:8]
    
    try:
        await websocket.send_json({
            "type": "widget_connected",
            "session_id": session_id,
            "business_slug": business_slug,
        })

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif message.get("type") == "message":
                    # Echo back confirmation and simulate AI thinking
                    await websocket.send_json({
                        "type": "message_received",
                        "message_id": str(uuid.uuid4())[:8],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.debug(f"Widget disconnected: {business_slug}/{session_id}")
