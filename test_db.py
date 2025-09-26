#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from sqlalchemy import create_engine, text

# Configurar encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_connection():
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/gestor_tarefas"

    try:
        # Testar conexão
        engine = create_engine(DATABASE_URL)

        # Testar consulta básica
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Conexao PostgreSQL OK")

        # Testar se banco existe
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.fetchone()[0]
            print(f"Banco atual: {db_name}")

    except Exception as e:
        print(f"Erro: {e}")

        # Tentar conectar no banco postgres padrão para criar o banco
        try:
            default_url = "postgresql://postgres:postgres@localhost:5432/postgres"
            default_engine = create_engine(default_url)

            with default_engine.connect() as conn:
                # Verificar se banco existe
                result = conn.execute(text(
                    "SELECT 1 FROM pg_database WHERE datname = 'gestor_tarefas'"
                ))

                if not result.fetchone():
                    print("Criando banco gestor_tarefas...")
                    conn.execute(text("COMMIT"))
                    conn.execute(text("CREATE DATABASE gestor_tarefas"))
                    print("Banco criado com sucesso!")
                else:
                    print("Banco gestor_tarefas ja existe")

        except Exception as e2:
            print(f"Erro ao criar banco: {e2}")

if __name__ == "__main__":
    test_connection()