from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.websocket import ConnectionManager
import asyncio
import json
from app.core import pubsub

router = APIRouter()
manager = ConnectionManager()


async def redis_listener():
    """Background task to listen for Redis pub/sub messages and broadcast to WebSocket clients"""
    while True:
        try:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                print(f"Broadcasting message to {len(manager.active_connections)} clients: {data}")
                await manager.broadcast(data)
        except Exception as e:
            print(f"Error in redis_listener: {e}")
        await asyncio.sleep(0.1)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client disconnected. Active connections: {len(manager.active_connections)}")
