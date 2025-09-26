#!/usr/bin/env python3
"""
Script para criar usuários de teste no banco de dados
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.auth import get_password_hash
from app.models.users import User, UserRole
from app.core.database import Base

def create_test_users():
    """Criar usuários de teste se não existirem"""

    # Criar engine e sessão
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Criar tabelas se não existirem
    print("Criando tabelas se necessário...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Usuários de teste
        test_users = [
            {
                "username": "admin",
                "password": "admin123",
                "email": "admin@gmx.com",
                "role": UserRole.ADMIN.value,
                "isActive": True
            },
            {
                "username": "comercial",
                "password": "comercial123",
                "email": "comercial@gmx.com",
                "role": UserRole.COMERCIAL.value,
                "isActive": True
            },
            {
                "username": "suprimentos",
                "password": "suprimentos123",
                "email": "suprimentos@gmx.com",
                "role": UserRole.SUPRIMENTOS.value,
                "isActive": True
            },
            {
                "username": "diretoria",
                "password": "diretoria123",
                "email": "diretoria@gmx.com",
                "role": UserRole.DIRETORIA.value,
                "isActive": True
            }
        ]

        print("Verificando usuários existentes...")

        for user_data in test_users:
            # Verificar se usuário já existe
            existing_user = db.query(User).filter(User.username == user_data["username"]).first()

            if existing_user:
                print(f"Usuario '{user_data['username']}' ja existe")
                continue

            # Criar novo usuário
            hashed_password = get_password_hash(user_data["password"])
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                password=hashed_password,  # Usar o campo correto do modelo
                role=user_data["role"],
                isActive=user_data["isActive"]
            )

            db.add(new_user)
            print(f"Criado usuario '{user_data['username']}' com role '{user_data['role']}'")

        # Salvar alterações
        db.commit()
        print("\nUsuarios de teste criados com sucesso!")

        # Listar usuários criados
        users = db.query(User).all()
        print(f"\nTotal de usuarios no banco: {len(users)}")
        for user in users:
            print(f"   - {user.username} ({user.role}) - Ativo: {user.isActive}")

    except Exception as e:
        print(f"Erro ao criar usuarios: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando criacao de usuarios de teste...")
    create_test_users()
    print("Processo concluido!")