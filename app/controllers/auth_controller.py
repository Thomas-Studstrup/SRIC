from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from db.session import get_session
from models.user_model import User
from schemas.token_schema import TokenData
from schemas.user_schema import UserCreate

# 🔐 OAuth2-afhængighed
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# 🔐 Password-hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🔁 FastAPI-router
router = APIRouter(prefix="/auth", tags=["Auth"])

# 🎟 JWT access token generator
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 🔑 Auth: Hent bruger baseret på token
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ugyldigt login",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

# 👤 Register-endpoint (bruges kun hvis du vil tillade tilmelding uden login)
@router.post("/register")
def register_user(
    user: UserCreate = Body(...),
    db: Session = Depends(get_session)
):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Brugernavn er allerede i brug.")

    hashed_pw = pwd_context.hash(user.password)
    new_user = User(
        username=user.username,
        hashed_password=hashed_pw,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "message": "Bruger oprettet",
        "username": new_user.username,
        "role": new_user.role
    }
