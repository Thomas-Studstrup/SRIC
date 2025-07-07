from typing import List
from pydantic import BaseModel
from datetime import datetime

class ChatCreate(BaseModel):
    title: str

class ChatResponse(BaseModel):
    id: int
    title: str
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True