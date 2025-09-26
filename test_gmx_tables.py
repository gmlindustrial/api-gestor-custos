#!/usr/bin/env python3
"""Teste das tabelas GMX criadas"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime

load_dotenv()

def test_gmx_tables():
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            print("Testando inserção de dados básicos...")

            # Verificar se existe algum usuário
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"Usuários existentes: {user_count}")

            # Testar inserção de um centro de custo
            conn.execute(text("""
                INSERT INTO cost_centers (codigo, nome, descricao, tipo, is_active)
                VALUES ('MAT', 'Matéria-Prima', 'Centro de custo para materiais', 'material', true)
                ON CONFLICT (codigo) DO NOTHING
            """))

            # Testar inserção de um fornecedor
            conn.execute(text("""
                INSERT INTO suppliers (nome, cnpj, email, telefone, endereco, is_active)
                VALUES ('Fornecedor Teste LTDA', '12.345.678/0001-99', 'contato@fornecedorteste.com',
                       '11999999999', 'Rua Teste, 123', true)
                ON CONFLICT (cnpj) DO NOTHING
            """))

            # Testar inserção de um contrato
            conn.execute(text("""
                INSERT INTO contracts (nome, numero_contrato, tipo, cliente_nome, data_inicio,
                       data_fim, valor_total, status)
                VALUES ('Contrato Teste', 'CT-2024-001', 'material', 'Cliente Teste LTDA',
                       CURRENT_DATE, CURRENT_DATE + INTERVAL '6 months', 100000.00, 'ativo')
                ON CONFLICT (numero_contrato) DO NOTHING
            """))

            conn.commit()

            # Verificar dados inseridos
            result = conn.execute(text("SELECT COUNT(*) FROM cost_centers"))
            cc_count = result.scalar()

            result = conn.execute(text("SELECT COUNT(*) FROM suppliers"))
            supplier_count = result.scalar()

            result = conn.execute(text("SELECT COUNT(*) FROM contracts"))
            contract_count = result.scalar()

            print(f"Centros de custo: {cc_count}")
            print(f"Fornecedores: {supplier_count}")
            print(f"Contratos: {contract_count}")

            print("✓ Teste das tabelas GMX concluído com sucesso!")
            return True

    except Exception as e:
        print(f"✗ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    test_gmx_tables()