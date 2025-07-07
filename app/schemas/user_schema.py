from pydantic import BaseModel
from typing import Literal

class UserCreate(BaseModel):
    username: str
    password: str
    role: Literal["admin", "medarbejder", "ekstern"]

class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        orm_mode = True
