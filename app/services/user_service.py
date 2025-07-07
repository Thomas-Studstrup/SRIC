from sqlalchemy.orm import Session
from models.user_model import User
from db.session import get_session
import bcrypt


def get_user_by_username(username: str, db: Session = None):
    if db is None:
        db = next(get_session())
    return db.query(User).filter(User.username == username).first()

def create_user(username: str, password: str, role: str = "ekstern", db: Session = None):
    if db is None:
        db = next(get_session())
    
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise ValueError("Brugernavnet er allerede i brug.")
    
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(username=username, hashed_password=hashed_pw, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

