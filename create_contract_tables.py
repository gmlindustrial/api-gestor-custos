#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para criar tabelas de contratos completas no PostgreSQL"""

from sqlalchemy import create_engine, text
import sys
import os

# URL de conexão direta
DATABASE_URL = "postgresql://postgres:Digitalsegurogml2024!@localhost:5432/gestor_tarefas"

def create_contract_tables():
    """Criar todas as tabelas relacionadas ao módulo de contratos"""
    try:
        engine = create_engine(DATABASE_URL, echo=False)

        commands = [
            # Criar tipos ENUM
            """CREATE TYPE contract_type_enum AS ENUM ('material_produto', 'servico')""",
            """CREATE TYPE contract_status_enum AS ENUM ('ativo', 'concluido', 'cancelado', 'suspenso')""",

            # Criar tabela de contratos
            """CREATE TABLE IF NOT EXISTS contracts (
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
            )""",

            # Criar tabela de itens do orçamento
            """CREATE TABLE IF NOT EXISTS budget_items (
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
            )""",

            # Criar função para triggers
            """CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'""",

            # Criar triggers
            """CREATE TRIGGER update_contracts_updated_at BEFORE UPDATE ON contracts
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()""",
            """CREATE TRIGGER update_budget_items_updated_at BEFORE UPDATE ON budget_items
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()""",

            # Criar índices
            """CREATE INDEX IF NOT EXISTS idx_contracts_numero_contrato ON contracts(numero_contrato)""",
            """CREATE INDEX IF NOT EXISTS idx_contracts_cliente ON contracts(cliente)""",
            """CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status)""",
            """CREATE INDEX IF NOT EXISTS idx_contracts_criado_por ON contracts(criado_por)""",
            """CREATE INDEX IF NOT EXISTS idx_budget_items_contract_id ON budget_items(contract_id)""",
            """CREATE INDEX IF NOT EXISTS idx_budget_items_codigo_item ON budget_items(codigo_item)""",
            """CREATE INDEX IF NOT EXISTS idx_budget_items_centro_custo ON budget_items(centro_custo)""",
        ]

        # Executar comandos um por um
        with engine.connect() as connection:
            for i, command in enumerate(commands):
                try:
                    connection.execute(text(command))
                    connection.commit()
                    print(f"[OK] Comando {i+1} executado com sucesso")
                except Exception as e:
                    if "already exists" in str(e) or "duplicate key" in str(e):
                        print(f"[SKIP] Comando {i+1}: {str(e)[:100]}...")
                    else:
                        print(f"[ERRO] Comando {i+1}: {str(e)[:200]}...")

        # Inserir dados de teste
        insert_commands = [
            """INSERT INTO contracts (
                numero_contrato, nome_projeto, cliente, tipo_contrato, valor_original,
                meta_reducao_percentual, status, data_inicio, data_fim_prevista, criado_por
            ) VALUES
            ('CNT-2025-001', 'Edifício Residencial - Zona Sul', 'Construtora ABC', 'material_produto',
             2400000.00, 10.0, 'ativo', '2025-01-15', '2025-12-15',
             (SELECT id FROM users WHERE username = 'admin' LIMIT 1))
            ON CONFLICT (numero_contrato) DO NOTHING""",

            """INSERT INTO contracts (
                numero_contrato, nome_projeto, cliente, tipo_contrato, valor_original,
                meta_reducao_percentual, status, data_inicio, data_fim_prevista, criado_por
            ) VALUES
            ('CNT-2025-002', 'Complexo Comercial - Centro', 'Incorporadora XYZ', 'servico',
             1800000.00, 8.0, 'ativo', '2025-03-10', '2025-11-10',
             (SELECT id FROM users WHERE username = 'admin' LIMIT 1))
            ON CONFLICT (numero_contrato) DO NOTHING""",

            """INSERT INTO contracts (
                numero_contrato, nome_projeto, cliente, tipo_contrato, valor_original,
                meta_reducao_percentual, status, data_inicio, data_fim_prevista, criado_por
            ) VALUES
            ('CNT-2024-003', 'Infraestrutura Urbana - Norte', 'Prefeitura Municipal', 'material_produto',
             950000.00, 15.0, 'ativo', '2024-11-01', '2025-06-01',
             (SELECT id FROM users WHERE username = 'admin' LIMIT 1))
            ON CONFLICT (numero_contrato) DO NOTHING"""
        ]

        with engine.connect() as connection:
            for i, command in enumerate(insert_commands):
                try:
                    connection.execute(text(command))
                    connection.commit()
                    print(f"[OK] Dados de exemplo {i+1} inseridos")
                except Exception as e:
                    print(f"[SKIP] Dados {i+1}: {str(e)[:100]}...")

        print("SUCCESS: Tabelas de contratos criadas com sucesso!")

    except Exception as e:
        print(f"ERROR: Erro ao criar tabelas: {e}")
        return False

    return True

def verify_tables():
    """Verificar se as tabelas foram criadas corretamente"""
    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as connection:
            # Verificar se as tabelas existem
            result = connection.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('contracts', 'budget_items')
                ORDER BY table_name
            """))

            tables = [row[0] for row in result]
            print(f"✓ Tabelas encontradas: {', '.join(tables)}")

            # Verificar dados de exemplo
            result = connection.execute(text("SELECT COUNT(*) FROM contracts"))
            contract_count = result.fetchone()[0]
            print(f"✓ Contratos de exemplo: {contract_count}")

            result = connection.execute(text("SELECT COUNT(*) FROM budget_items"))
            budget_count = result.fetchone()[0]
            print(f"✓ Itens de orçamento de exemplo: {budget_count}")

    except Exception as e:
        print(f"✗ Erro ao verificar tabelas: {e}")
        return False

    return True

if __name__ == "__main__":
    print("Criando tabelas de contratos...")
    success = create_contract_tables()

    if success:
        print("\nVerificando tabelas criadas...")
        verify_tables()

    sys.exit(0 if success else 1)