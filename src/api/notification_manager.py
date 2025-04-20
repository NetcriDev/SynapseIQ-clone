
import asyncio
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import json
# {
#   "type": "new_incident",
#   "report_number": "202504011245",
#   "message": "New incident report received",
#   "timestamp": "2025-04-18T12:34:56"
# }

connected_clients: List[WebSocket] = []

REDIS_CHANNEL = "incident_notifications"

async def notify_new_incident_to_clients(data: dict):
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(data)
        except:
            disconnected.append(client)
    for client in disconnected:
        connected_clients.remove(client)

async def redis_subscriber():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL)
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            await notify_new_incident_to_clients(data)






### REvisar lo de abajo





connected_clients: List[WebSocket] = []

async def notify_new_incident(report_number: str, state: str, city: str, injury_severity: str, date: str):
    message = {
        "type": "new_incident",
        "report_number": report_number,
        "state": state,
        "city": city,
        "injury_severity": injury_severity,
        "timestamp": date,
        "message": "New incident report received",
    }

    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except WebSocketDisconnect:
            disconnected.append(client)

    for client in disconnected:
        connected_clients.remove(client)


def send_notification(report_number: str, state: str, city: str, injury_severity: str, date: str):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(notify_new_incident(report_number, state, city, injury_severity, date))
    else:
        loop.run_until_complete(notify_new_incident(report_number, state, city, injury_severity, date))








