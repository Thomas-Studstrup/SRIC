from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.base_class import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    role = Column(String, nullable=False)  # 'user' eller 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON string af kilder
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")