from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_session
from schemas.chat_schema import ChatCreate, ChatResponse
from schemas.message_schema import MessageCreate, MessageResponse
from services.chat_service import create_chat, get_user_chats, add_message, get_chat_messages
from controllers.auth_controller import get_current_user
from models.user_model import User
from typing import List

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("/", response_model=ChatResponse)
def create_new_chat(chat_data: ChatCreate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return create_chat(db, chat_data, user)

@router.get("/", response_model=List[ChatResponse])
def list_user_chats(db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return get_user_chats(db, user)

@router.post("/messages/", response_model=MessageResponse)
def send_message(message_data: MessageCreate, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return add_message(db, message_data, user)

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
def get_messages(chat_id: int, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return get_chat_messages(db, chat_id)