from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# session_id -> list of connected peer WebSockets (customer + technician, 1-on-1 room)
_active_rooms: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/video/signal/{session_id}")
async def webrtc_signaling_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    room = _active_rooms.setdefault(session_id, [])
    room.append(websocket)

    try:
        while True:
            # {"type": "offer" | "answer" | "ice_candidate", "payload": {...}}
            message = await websocket.receive_json()
            for peer in room:
                if peer is not websocket:
                    await peer.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        room.remove(websocket)
        if not room:
            _active_rooms.pop(session_id, None)
