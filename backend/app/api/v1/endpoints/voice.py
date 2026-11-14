import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, AsyncSessionLocal
from app.services.voice_engine import VoiceSessionHandler
from app.models.models import VoiceSession, SessionStatus

router = APIRouter()

@router.websocket("/live")
async def websocket_voice_live(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        # Create voice session record in DB
        voice_session = VoiceSession(
            id=session_id,
            language="gu-IN",
            status=SessionStatus.ACTIVE.value
        )
        db.add(voice_session)
        await db.commit()

        handler = VoiceSessionHandler(websocket=websocket, db=db, session_id=session_id)
        try:
            await handler.run()
        except WebSocketDisconnect:
            pass
        finally:
            voice_session.status = SessionStatus.COMPLETED.value
            await db.commit()
