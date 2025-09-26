#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para corrigir senhas dos usuários"""

from sqlalchemy import create_engine, text
from app.core.auth import get_password_hash

# URL de conexão
DATABASE_URL = "postgresql://postgres:Digitalsegurogml2024!@localhost:5432/gestor_tarefas"

def fix_user_passwords():
    """Atualizar senhas dos usuários para formato hash bcrypt"""
    try:
        engine = create_engine(DATABASE_URL, echo=False)

        # Senhas padrão para os usuários
        users_passwords = [
            {"username": "admin", "password": "admin123"},
            {"username": "teste1", "password": "teste123"},
            {"username": "Bruno Brito", "password": "bruno123"},
            {"username": "Daniel Rodrigues", "password": "daniel123"},
        ]

        with engine.connect() as conn:
            for user_data in users_passwords:
                # Gerar hash da senha
                hashed_password = get_password_hash(user_data["password"])

                # Atualizar senha no banco
                result = conn.execute(text("""
                    UPDATE users
                    SET password = :password
                    WHERE username = :username
                """), {
                    "password": hashed_password,
                    "username": user_data["username"]
                })

                if result.rowcount > 0:
                    print(f"[OK] Senha atualizada para usuário: {user_data['username']}")
                else:
                    print(f"[SKIP] Usuário não encontrado: {user_data['username']}")

                conn.commit()

        print("Senhas atualizadas com sucesso!")
        print("\nCredenciais de login:")
        for user_data in users_passwords:
            print(f"  {user_data['username']}: {user_data['password']}")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    fix_user_passwords()