import asyncio

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings

router = APIRouter()


@router.websocket("/ws/canvas/sync/{session_id}")
async def canvas_sync_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    channel = f"canvas_sync:{session_id}"
    await pubsub.subscribe(channel)

    async def redis_listener():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except Exception:
            pass

    listener_task = asyncio.create_task(redis_listener())
    try:
        while True:
            # {"action": "DRAW", "norm_x": 0.452, "norm_y": 0.781, "color": "#FF0000"}
            raw_data = await websocket.receive_text()
            await redis_client.publish(channel, raw_data)
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await redis_client.aclose()
