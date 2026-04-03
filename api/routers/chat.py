from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_app_db
from models.conversation import Conversation, ConversationMessage
from schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    MessageResponse,
)
from services.agent import chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(body: ChatRequest):
    response_text = await chat(body.session_id, body.message)
    return ChatResponse(session_id=body.session_id, response=response_text)


@router.get("/sessions", response_model=list[ConversationResponse])
async def list_sessions(db: AsyncSession = Depends(get_app_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.last_active_at.desc())
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=list[MessageResponse])
async def get_session_history(
    session_id: str, db: AsyncSession = Depends(get_app_db)
):
    result = await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.created_at)
    )
    return result.scalars().all()
