from sqlalchemy.orm import Session
from models.user_model import User, UserRole
from db.session import get_session
import bcrypt


def get_all_roles():
    """Returnerer alle mulige brugerroller som liste af str til frontend."""
    return [role.value for role in UserRole]

def get_user_by_username(username: str, db: Session = None):
    if db is None:
        db = next(get_session())
    return db.query(User).filter(User.username == username).first()

def create_user(username: str, password: str, role: str = "ekstern", db: Session = None):
    if db is None:
        db = next(get_session())

    # Valider rolle
    allowed_roles = get_all_roles()
    if role not in allowed_roles:
        raise ValueError(f"Ugyldig rolle: {role}. Mulige roller: {allowed_roles}")

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

