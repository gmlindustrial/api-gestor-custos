from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    COMERCIAL = "comercial"
    SUPRIMENTOS = "suprimentos"
    DIRETORIA = "diretoria"
    CLIENTE = "cliente"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)
    password = Column(String, nullable=True)  # Campo real do banco existente
    isActive = Column(Boolean, default=True)  # Campo real do banco existente
    role = Column(String, nullable=False)

    # Propriedades para compatibilidade
    @property
    def full_name(self):
        return self.username

    @property
    def hashed_password(self):
        return self.password

    @property
    def is_active(self):
        return self.isActive