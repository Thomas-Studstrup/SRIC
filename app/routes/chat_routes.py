from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from db.session import get_session
from schemas.chat_schema import ChatCreate, ChatResponse
from schemas.message_schema import MessageCreate, MessageResponse, ChatResponse as MessageChatResponse
from controllers.auth_controller import get_current_user
from models.user_model import User
from models.chat_model import Chat
from models.message_model import Message
from services.conversation_service import process_contextual_query

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("/", response_model=ChatResponse)
def create_new_chat(
    chat_data: ChatCreate, 
    db: Session = Depends(get_session), 
    user: User = Depends(get_current_user)
):
    """Opret en ny chat"""
    new_chat = Chat(
        title=chat_data.title,
        owner_id=user.id
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    
    # Return chat without messages for initial creation
    return ChatResponse(
        id=new_chat.id,
        title=new_chat.title,
        owner_id=new_chat.owner_id,
        created_at=new_chat.created_at,
        messages=[]  # Empty messages list for new chat
    )

@router.get("/", response_model=List[ChatResponse])
def list_user_chats(
    db: Session = Depends(get_session), 
    user: User = Depends(get_current_user)
):
    """Hent alle chats for brugeren"""
    chats = db.query(Chat).filter(Chat.owner_id == user.id).order_by(Chat.created_at.desc()).all()
    
    # Return chats without messages for list view
    chat_responses = []
    for chat in chats:
        chat_responses.append(ChatResponse(
            id=chat.id,
            title=chat.title,
            owner_id=chat.owner_id,
            created_at=chat.created_at,
            messages=[]  # Empty messages list for chat list
        ))
    
    return chat_responses

@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat_with_messages(
    chat_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Hent en specifik chat med alle beskeder"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id, 
        Chat.owner_id == user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat ikke fundet")
    
    # Manually fetch messages with the new structure
    messages = db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.created_at.asc()).all()
    
    # Convert messages to response format
    message_responses = []
    for msg in messages:
        message_responses.append(MessageResponse(
            id=msg.id,
            chat_id=msg.chat_id,
            role=msg.role,
            content=msg.content,
            sources=msg.sources,
            created_at=msg.created_at
        ))
    
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        owner_id=chat.owner_id,
        created_at=chat.created_at,
        messages=message_responses
    )

@router.post("/{chat_id}/message", response_model=MessageChatResponse)
def send_message(
    chat_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Send en besked til en chat med kontekst"""
    # Verificer at chatten tilhører brugeren
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.owner_id == user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat ikke fundet")
    
    # Hent tidligere beskeder for kontekst
    previous_messages = db.query(Message).filter(
        Message.chat_id == chat_id
    ).order_by(Message.created_at.asc()).all()
    
    # Konverter til format som rag_service forventer
    conversation_history = []
    for msg in previous_messages:
        conversation_history.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Gem brugerens besked
    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=message_data.content
    )
    db.add(user_message)
    db.flush()  # Få ID uden at committe endnu
    
    # Behandl spørgsmål med kontekst og få svar
    try:
        answer, sources = process_contextual_query(
            message_data.content, 
            conversation_history
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Fejl ved generering af svar: {str(e)}")
    
    # Gem assistentens svar
    assistant_message = Message(
        chat_id=chat_id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources) if sources else None
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    return MessageChatResponse(
        chat_id=chat_id,
        message=assistant_message,
        sources=sources
    )

@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Slet en chat og alle dens beskeder"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.owner_id == user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat ikke fundet")
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat slettet"}

# TEST ENDPOINT
@router.get("/test")
def test_chat_routes():
    """Test endpoint for at tjekke om chat routes virker"""
    return {"message": "Chat routes virker!", "timestamp": "2025-01-07"}