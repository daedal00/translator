from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth, ingest, sessions, ws
from app.core.config import settings
from app.core.ratelimit import limiter
from app.db.session import init_db
from app.pipeline.stt import STTPipeline
from app.pipeline.translate import NLLBTranslator


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.stt = STTPipeline(model_size=settings.whisper_model, device=settings.whisper_device)
    app.state.translator = NLLBTranslator(model_name=settings.nllb_model, device=settings.nllb_device)
    yield
    # cleanup if needed


app = FastAPI(title="Sermon Translator", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(ingest.router)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"ok": True}
