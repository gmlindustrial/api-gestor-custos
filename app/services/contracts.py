from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
from app.models.contracts import Contract, BudgetItem
from app.models.purchases import PurchaseOrder, Invoice
from app.schemas.contracts import ContractCreate, ContractUpdate, ContractResponse
from fastapi import HTTPException, status


class ContractService:
    def __init__(self, db: Session):
        self.db = db

    def create_contract(self, contract_data: ContractCreate, created_by: int) -> Contract:
        # Verificar se o número do contrato já existe
        existing_contract = self.db.query(Contract).filter(
            Contract.numero_contrato == contract_data.numero_contrato
        ).first()
        
        if existing_contract:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Número de contrato já existe"
            )

        # Criar o contrato
        contract = Contract(
            numero_contrato=contract_data.numero_contrato,
            nome_projeto=contract_data.nome_projeto,
            cliente=contract_data.cliente,
            tipo_contrato=contract_data.tipo_contrato,
            valor_original=contract_data.valor_original,
            meta_reducao_percentual=contract_data.meta_reducao_percentual,
            data_inicio=contract_data.data_inicio,
            data_fim_prevista=contract_data.data_fim_prevista,
            observacoes=contract_data.observacoes,
            criado_por=created_by
        )

        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)

        # Criar itens do orçamento
        for item_data in contract_data.budget_items:
            budget_item = BudgetItem(
                contract_id=contract.id,
                **item_data.dict()
            )
            self.db.add(budget_item)

        self.db.commit()
        return contract

    def get_contract_by_id(self, contract_id: int) -> Optional[Contract]:
        return self.db.query(Contract).filter(Contract.id == contract_id).first()

    def get_contracts(
        self, 
        skip: int = 0, 
        limit: int = 10,
        cliente: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Contract]:
        query = self.db.query(Contract)
        
        if cliente:
            query = query.filter(Contract.cliente.ilike(f"%{cliente}%"))
        
        if status:
            query = query.filter(Contract.status == status)
        
        return query.offset(skip).limit(limit).all()

    def update_contract(self, contract_id: int, contract_data: ContractUpdate) -> Optional[Contract]:
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            return None

        update_data = contract_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contract, field, value)

        self.db.commit()
        self.db.refresh(contract)
        return contract

    def delete_contract(self, contract_id: int) -> bool:
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            return False

        # Verificar se há compras associadas
        has_purchases = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.contract_id == contract_id
        ).first()

        if has_purchases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível excluir contrato com compras associadas"
            )

        self.db.delete(contract)
        self.db.commit()
        return True

    def calculate_contract_metrics(self, contract_id: int) -> dict:
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            return {}

        # Calcular valor realizado (soma das faturas)
        valor_realizado = self.db.query(func.sum(Invoice.valor_total)).join(
            PurchaseOrder
        ).filter(PurchaseOrder.contract_id == contract_id).scalar() or Decimal('0')

        # Calcular saldo do contrato
        saldo_contrato = contract.valor_original - valor_realizado

        # Calcular percentual realizado
        percentual_realizado = (valor_realizado / contract.valor_original * 100) if contract.valor_original > 0 else Decimal('0')

        # Calcular valor previsto total
        valor_previsto = self.db.query(func.sum(BudgetItem.valor_total_previsto)).filter(
            BudgetItem.contract_id == contract_id
        ).scalar() or contract.valor_original

        # Calcular economia (previsto - realizado)
        economia_obtida = valor_previsto - valor_realizado
        percentual_economia = (economia_obtida / valor_previsto * 100) if valor_previsto > 0 else Decimal('0')

        return {
            'valor_realizado': valor_realizado,
            'saldo_contrato': saldo_contrato,
            'percentual_realizado': percentual_realizado,
            'economia_obtida': economia_obtida,
            'percentual_economia': percentual_economia,
            'meta_atingida': percentual_economia >= contract.meta_reducao_percentual
        }