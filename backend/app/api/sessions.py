from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import generate_session_code
from app.db.models import Session, User
from app.db.session import get_db
from app.pipeline.hub import hub

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: str = ""
    source_lang: str = "ko"


class SessionOut(BaseModel):
    id: int
    code: str
    title: str
    source_lang: str
    is_live: bool
    attendees: int


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code = generate_session_code()
    while await db.scalar(select(Session).where(Session.code == code)):
        code = generate_session_code()

    session = Session(org_id=user.org_id, code=code, title=body.title, source_lang=body.source_lang)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionOut(
        id=session.id,
        code=session.code,
        title=session.title,
        source_lang=session.source_lang,
        is_live=session.is_live,
        attendees=hub.attendee_count(session.code),
    )


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(
        select(Session).where(Session.org_id == user.org_id).order_by(Session.created_at.desc())
    )
    return [
        SessionOut(
            id=s.id,
            code=s.code,
            title=s.title,
            source_lang=s.source_lang,
            is_live=s.is_live,
            attendees=hub.attendee_count(s.code),
        )
        for s in rows
    ]


@router.post("/{code}/start")
async def start_session(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.scalar(select(Session).where(Session.code == code))
    if not session or session.org_id != user.org_id:
        raise HTTPException(status_code=404)
    session.is_live = True
    await db.commit()
    return {"ok": True}


@router.post("/{code}/end")
async def end_session(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.scalar(select(Session).where(Session.code == code))
    if not session or session.org_id != user.org_id:
        raise HTTPException(status_code=404)
    session.is_live = False
    session.ended_at = datetime.now(UTC)
    await db.commit()
    await hub.broadcast(code, {"type": "session_ended"})
    return {"ok": True}
