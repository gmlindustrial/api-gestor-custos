#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para corrigir enums no banco"""

import os
from sqlalchemy import create_engine, text

# Force UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PGCLIENTENCODING'] = 'utf8'

DATABASE_URL = "postgresql://postgres:Digitalsegurogml2024!@localhost:5432/gestor_tarefas"

def fix_enum_issues():
    """Corrigir problemas de enum no banco"""
    try:
        engine = create_engine(DATABASE_URL, echo=False)

        with engine.connect() as conn:
            # Verificar valores atuais
            print("Verificando tipos de contrato atuais...")
            result = conn.execute(text("SELECT DISTINCT tipo_contrato FROM contracts"))
            current_types = [row[0] for row in result]
            print(f"Tipos encontrados: {current_types}")

            # Verificar valores de status atuais
            print("Verificando status atuais...")
            result = conn.execute(text("SELECT DISTINCT status FROM contracts"))
            current_status = [row[0] for row in result]
            print(f"Status encontrados: {current_status}")

            print("Tabela verificada com sucesso!")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    fix_enum_issues()