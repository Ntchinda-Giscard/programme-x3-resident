
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database.session import get_db
from pydantic import BaseModel
from typing import Optional, List
from .service import process_chat_message

chat_router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

@chat_router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        result = await process_chat_message(db, request.query, request.conversation_id)
        return ChatResponse(**result)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
