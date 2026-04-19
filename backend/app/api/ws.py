"""
WebSocket endpoint for attendees.
ws://<host>/ws/<session_code>?lang=en
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session
from app.db.session import AsyncSessionLocal
from app.pipeline.hub import hub

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{code}")
async def attendee_ws(code: str, ws: WebSocket, lang: str = "en"):
    async with AsyncSessionLocal() as db:
        session = await db.scalar(select(Session).where(Session.code == code))
        if not session:
            await ws.close(code=4404, reason="Session not found")
            return

    await ws.accept()
    hub.join(code, ws)
    try:
        await ws.send_json({"type": "joined", "code": code, "lang": lang})
        while True:
            # Keep connection open; clients may send lang change messages
            msg = await ws.receive_json()
            if msg.get("type") == "set_lang":
                lang = msg.get("lang", lang)
    except WebSocketDisconnect:
        pass
    finally:
        hub.leave(code, ws)
