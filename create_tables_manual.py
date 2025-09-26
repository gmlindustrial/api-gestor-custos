#!/usr/bin/env python3
"""Script para criar tabelas manualmente sem usar Alembic"""

from sqlalchemy import create_engine, text
import sys
import os

# URL de conexão usando variáveis do .env
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/gestor_tarefas")

def create_tables():
    try:
        engine = create_engine(DATABASE_URL, echo=True)

        # Usar SQLAlchemy para criar as tabelas dos modelos GMX
        from app.core.database import Base
        from app.models.contracts import Contract, BudgetItem
        from app.models.purchases import Supplier, PurchaseOrder, PurchaseOrderItem, Quotation, Invoice, InvoiceItem
        from app.models.attachments import Attachment
        from app.models.audit import AuditLog
        from app.models.cost_centers import CostCenter
        # Não importar User pois já existe

        print("Criando tabelas do GMX (preservando existentes)...")
        # Criar apenas tabelas que não existem
        Base.metadata.create_all(bind=engine, checkfirst=True)

        create_sql = """
        -- Script executado com sucesso
        SELECT 1;
        """

        with engine.connect() as connection:
            connection.execute(text(create_sql))
            connection.commit()
            print("✓ Tabelas criadas com sucesso!")

    except Exception as e:
        print(f"✗ Erro ao criar tabelas: {e}")
        return False

    return True

if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)