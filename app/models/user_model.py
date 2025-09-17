# app/models/user_model.py
from sqlalchemy import Column, Integer, String, Enum
from db.base_class import Base  # 👈 brug fælles base
import enum

class UserRole(str, enum.Enum):
    admin = "Admin"
    medarbejder = "Medarbejder"
    ekstern = "Ekstern"
    client_service = "Client Service"
    business_management = "Business Management"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
