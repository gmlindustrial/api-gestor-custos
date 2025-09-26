#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script simples para criar tabelas de contratos"""

from sqlalchemy import create_engine, text
import sys

# URL de conexão direta
DATABASE_URL = "postgresql://postgres:Digitalsegurogml2024!@localhost:5432/gestor_tarefas"

def execute_sql(engine, sql, description):
    """Executa um comando SQL e trata erros"""
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print(f"[OK] {description}")
        return True
    except Exception as e:
        if "already exists" in str(e) or "duplicate key" in str(e):
            print(f"[SKIP] {description} - ja existe")
        else:
            print(f"[ERROR] {description}: {str(e)[:150]}...")
        return False

def main():
    print("Criando tabelas de contratos...")
    engine = create_engine(DATABASE_URL, echo=False)

    # 1. Criar tipos enum se não existem
    execute_sql(engine,
        "CREATE TYPE contract_type_enum AS ENUM ('material_produto', 'servico')",
        "Tipo ENUM contract_type_enum")

    execute_sql(engine,
        "CREATE TYPE contract_status_enum AS ENUM ('ativo', 'concluido', 'cancelado', 'suspenso')",
        "Tipo ENUM contract_status_enum")

    # 2. Criar tabela contracts
    contracts_sql = """
    CREATE TABLE contracts (
        id SERIAL PRIMARY KEY,
        numero_contrato VARCHAR(255) UNIQUE NOT NULL,
        nome_projeto VARCHAR(255) NOT NULL,
        cliente VARCHAR(255) NOT NULL,
        tipo_contrato contract_type_enum NOT NULL,
        valor_original DECIMAL(15,2) NOT NULL,
        meta_reducao_percentual DECIMAL(5,2) DEFAULT 0,
        status contract_status_enum DEFAULT 'ativo',
        data_inicio TIMESTAMP WITH TIME ZONE NOT NULL,
        data_fim_prevista TIMESTAMP WITH TIME ZONE,
        data_fim_real TIMESTAMP WITH TIME ZONE,
        observacoes TEXT,
        criado_por INTEGER REFERENCES users(id) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE
    )
    """
    execute_sql(engine, contracts_sql, "Tabela contracts")

    # 3. Criar tabela budget_items
    budget_items_sql = """
    CREATE TABLE budget_items (
        id SERIAL PRIMARY KEY,
        contract_id INTEGER REFERENCES contracts(id) NOT NULL,
        codigo_item VARCHAR(255) NOT NULL,
        descricao TEXT NOT NULL,
        centro_custo VARCHAR(255) NOT NULL,
        unidade VARCHAR(50),
        quantidade_prevista DECIMAL(15,4),
        peso_previsto DECIMAL(15,4),
        valor_unitario_previsto DECIMAL(15,2),
        valor_total_previsto DECIMAL(15,2) NOT NULL,
        horas_normais_previstas DECIMAL(10,2),
        horas_extras_previstas DECIMAL(10,2),
        salario_previsto DECIMAL(15,2),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE
    )
    """
    execute_sql(engine, budget_items_sql, "Tabela budget_items")

    # 4. Inserir dados de exemplo
    insert_sql = """
    INSERT INTO contracts (
        numero_contrato, nome_projeto, cliente, tipo_contrato,
        valor_original, meta_reducao_percentual, status,
        data_inicio, data_fim_prevista, criado_por
    ) VALUES
    ('CNT-2025-001', 'Edificio Residencial - Zona Sul', 'Construtora ABC', 'material_produto',
     2400000.00, 10.0, 'ativo', '2025-01-15', '2025-12-15', 1)
    ON CONFLICT (numero_contrato) DO NOTHING
    """
    execute_sql(engine, insert_sql, "Dados de exemplo")

    # 5. Verificar se funcionou
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM contracts"))
            count = result.fetchone()[0]
            print(f"[VERIFY] Contratos na tabela: {count}")

            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN ('contracts', 'budget_items')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            print(f"[VERIFY] Tabelas criadas: {', '.join(tables)}")

    except Exception as e:
        print(f"[ERROR] Verificacao: {e}")

    print("Concluido!")

if __name__ == "__main__":
    main()