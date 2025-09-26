#!/usr/bin/env python3
"""Script para inicializar banco SQLite para desenvolvimento"""

from sqlalchemy import create_engine
from app.core.database import Base
from app.models import *  # Importa todos os modelos
from app.core.auth import get_password_hash
import os

def init_database():
    # Criar engine SQLite
    engine = create_engine("sqlite:///./gestor_tarefas.db", echo=True)

    try:
        # Criar todas as tabelas
        Base.metadata.create_all(bind=engine)
        print("✓ Database e tabelas criadas com sucesso!")

        # Criar usuários de teste
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # Verificar se já existem usuários
            existing_users = db.query(User).count()
            if existing_users == 0:
                # Criar usuários de teste para cada role
                test_users = [
                    User(
                        username="admin",
                        email="admin@gmx.com",
                        full_name="Administrador",
                        hashed_password=get_password_hash("admin123"),
                        role="admin",
                        is_active=True
                    ),
                    User(
                        username="comercial",
                        email="comercial@gmx.com",
                        full_name="Usuario Comercial",
                        hashed_password=get_password_hash("comercial123"),
                        role="comercial",
                        is_active=True
                    ),
                    User(
                        username="suprimentos",
                        email="suprimentos@gmx.com",
                        full_name="Usuario Suprimentos",
                        hashed_password=get_password_hash("suprimentos123"),
                        role="suprimentos",
                        is_active=True
                    ),
                    User(
                        username="diretoria",
                        email="diretoria@gmx.com",
                        full_name="Usuario Diretoria",
                        hashed_password=get_password_hash("diretoria123"),
                        role="diretoria",
                        is_active=True
                    )
                ]

                for user in test_users:
                    db.add(user)

                db.commit()
                print("✓ Usuários de teste criados:")
                print("  - admin/admin123 (Administrador)")
                print("  - comercial/comercial123 (Comercial)")
                print("  - suprimentos/suprimentos123 (Suprimentos)")
                print("  - diretoria/diretoria123 (Diretoria)")
            else:
                print("✓ Usuários já existem no banco")

        except Exception as e:
            print(f"Erro ao criar usuários: {e}")
            db.rollback()
        finally:
            db.close()

    except Exception as e:
        print(f"Erro ao criar banco: {e}")
        return False

    return True

if __name__ == "__main__":
    success = init_database()
    exit(0 if success else 1)