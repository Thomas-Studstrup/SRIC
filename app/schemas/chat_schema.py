from typing import List
from pydantic import BaseModel
from datetime import datetime
from schemas.message_schema import MessageResponse

class ChatCreate(BaseModel):
    title: str

class ChatResponse(BaseModel):
    id: int
    title: str
    owner_id: int
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True