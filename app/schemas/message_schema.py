from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    sources: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    chat_id: int
    message: MessageResponse
    sources: List[str] = []