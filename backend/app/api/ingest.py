from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Session, User
from app.db.session import get_db
from app.ingest.webrtc import handle_offer

router = APIRouter(prefix="/ingest", tags=["ingest"])


class OfferIn(BaseModel):
    sdp: str
    type: str
    session_code: str


@router.post("/offer")
async def webrtc_offer(
    body: OfferIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.scalar(select(Session).where(Session.code == body.session_code))
    if not session or not session.is_live or session.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Session not found or not live")

    answer = await handle_offer(
        sdp=body.sdp,
        sdp_type=body.type,
        session_code=body.session_code,
        source_lang=session.source_lang,
        stt=request.app.state.stt,
        translator=request.app.state.translator,
    )
    return answer
