from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import verify_token
from app.models.users import User, UserRole
from typing import List

security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    user_identifier = verify_token(credentials.credentials)
    if user_identifier is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Buscar usuário por email (que é o que está no token) ou username (fallback)
    user = db.query(User).filter(
        (User.email == user_identifier) | (User.username == user_identifier)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


def require_roles(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


# Funções específicas para cada perfil
def get_comercial_user(current_user: User = Depends(require_roles([UserRole.COMERCIAL, UserRole.ADMIN]))):
    return current_user


def get_suprimentos_user(current_user: User = Depends(require_roles([UserRole.SUPRIMENTOS, UserRole.ADMIN]))):
    return current_user


def get_diretoria_user(current_user: User = Depends(require_roles([UserRole.DIRETORIA, UserRole.ADMIN]))):
    return current_user


def get_admin_user(current_user: User = Depends(require_roles([UserRole.ADMIN]))):
    return current_user