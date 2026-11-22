import uuid
from fastapi import APIRouter, WebSocket
from app.core.database import AsyncSessionLocal
from app.services.voice_engine import VoiceSessionHandler, gemini_configured
from app.core.config import settings
from app.models.models import VoiceSession, SessionStatus

router = APIRouter()


@router.get("/status")
async def voice_status():
    return {"gemini_configured": gemini_configured(), "live_model": settings.GEMINI_LIVE_MODEL,
            "vertex": settings.GOOGLE_GENAI_USE_VERTEXAI}


@router.websocket("/live")
async def websocket_voice_live(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        db.add(VoiceSession(id=session_id, language="multi", status=SessionStatus.ACTIVE.value))
        await db.commit()
    await VoiceSessionHandler(websocket=websocket, session_id=session_id).run()
