# ✅ auth_routes.py (repareret version)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from db.session import get_session
from models.user_model import User
from schemas.user_schema import UserCreate, UserResponse
from services.auth_service import (
    authenticate_user,
    create_access_token,
    get_password_hash
)
from services.user_service import get_all_roles

router = APIRouter(prefix="/auth", tags=["Auth"])

# 👤 GET CURRENT USER
@router.get("/roles")
def get_roles():
    """Returnerer alle mulige brugerroller til frontend."""
    return get_all_roles()
from controllers.auth_controller import get_current_user

# 🔐 LOGIN
@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ugyldigt brugernavn eller adgangskode",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# 👤 REGISTER
@router.post("/register", response_model=UserResponse)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_session)
):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brugernavn er allerede i brug"
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 👤 GET CURRENT USER
@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return current_user
