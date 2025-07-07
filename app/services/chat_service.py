from sqlalchemy.orm import Session
from models.chat_model import Chat
from models.message_model import Message
from schemas.chat_schema import ChatCreate
from schemas.message_schema import MessageCreate
from models.user_model import User

def create_chat(db: Session, chat_data: ChatCreate, user: User):
    new_chat = Chat(title=chat_data.title, owner_id=user.id)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat

def get_user_chats(db: Session, user: User):
    return db.query(Chat).filter(Chat.owner_id == user.id).all()

def add_message(db: Session, message_data: MessageCreate, user: User):
    message = Message(chat_id=message_data.chat_id, content=message_data.content, sender_id=user.id)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_chat_messages(db: Session, chat_id: int):
    return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp).all()