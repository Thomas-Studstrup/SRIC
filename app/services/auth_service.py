from datetime import datetime, timedelta
from typing import Optional
from datetime import timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models.user_model import User

# 🔐 Konfiguration (kan flyttes til config.py)
SECRET_KEY = "din_super_hemmelige_nøgle"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 dag

# 🔐 Password-hashing kontekst
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🔎 Verificer om plaintext password matcher hashed password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# 🔐 Hash et nyt password
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# 🔑 Bruges til login – tjekker bruger og password
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):  # type: ignore # Hvis der kommer en fejl her, er det sandsynligvis fordi `hashed_password` ikke er defineret i User-modellen
        return None
    return user

# 🧾 JWT token generator
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 🧾 JWT token decoder
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
