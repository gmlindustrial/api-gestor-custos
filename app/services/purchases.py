from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
from app.models.purchases import Supplier, PurchaseOrder, PurchaseOrderItem, Quotation, Invoice, InvoiceItem
from app.models.contracts import Contract
from app.schemas.purchases import (
    SupplierCreate, PurchaseOrderCreate, QuotationCreate, InvoiceCreate
)
from fastapi import HTTPException, status


class PurchaseService:
    def __init__(self, db: Session):
        self.db = db

    # Fornecedores
    def create_supplier(self, supplier_data: SupplierCreate) -> Supplier:
        # Verificar CNPJ único se fornecido
        if supplier_data.cnpj:
            existing_supplier = self.db.query(Supplier).filter(
                Supplier.cnpj == supplier_data.cnpj
            ).first()
            if existing_supplier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CNPJ já cadastrado"
                )

        supplier = Supplier(**supplier_data.dict())
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def get_suppliers(self, skip: int = 0, limit: int = 10, approved_only: bool = False) -> List[Supplier]:
        query = self.db.query(Supplier)
        if approved_only:
            query = query.filter(Supplier.is_approved == True)
        return query.offset(skip).limit(limit).all()

    def approve_supplier(self, supplier_id: int) -> Optional[Supplier]:
        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if supplier:
            supplier.is_approved = True
            self.db.commit()
            self.db.refresh(supplier)
        return supplier

    # Ordens de Compra
    def create_purchase_order(self, po_data: PurchaseOrderCreate, created_by: int) -> PurchaseOrder:
        # Verificar se o contrato existe
        contract = self.db.query(Contract).filter(Contract.id == po_data.contract_id).first()
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contrato não encontrado"
            )

        # Verificar se o fornecedor existe e está aprovado
        supplier = self.db.query(Supplier).filter(
            Supplier.id == po_data.supplier_id,
            Supplier.is_approved == True
        ).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor não encontrado ou não aprovado"
            )

        # Verificar número único da OC
        existing_po = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.numero_oc == po_data.numero_oc
        ).first()
        if existing_po:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Número da ordem de compra já existe"
            )

        # Calcular valor total dos itens
        valor_total = sum(item.valor_total for item in po_data.items)

        # Criar ordem de compra
        purchase_order = PurchaseOrder(
            contract_id=po_data.contract_id,
            numero_oc=po_data.numero_oc,
            supplier_id=po_data.supplier_id,
            valor_total=valor_total,
            data_emissao=po_data.data_emissao,
            data_entrega_prevista=po_data.data_entrega_prevista,
            observacoes=po_data.observacoes,
            justificativa_escolha=po_data.justificativa_escolha,
            criado_por=created_by
        )

        self.db.add(purchase_order)
        self.db.commit()
        self.db.refresh(purchase_order)

        # Criar itens da ordem de compra
        for item_data in po_data.items:
            item = PurchaseOrderItem(
                purchase_order_id=purchase_order.id,
                **item_data.dict()
            )
            self.db.add(item)

        # Criar cotações
        for quotation_data in po_data.quotations:
            quotation = Quotation(
                purchase_order_id=purchase_order.id,
                **quotation_data.dict()
            )
            self.db.add(quotation)

        self.db.commit()
        return purchase_order

    def get_purchase_orders(
        self, 
        skip: int = 0, 
        limit: int = 10,
        contract_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[PurchaseOrder]:
        query = self.db.query(PurchaseOrder)
        
        if contract_id:
            query = query.filter(PurchaseOrder.contract_id == contract_id)
        
        if status:
            query = query.filter(PurchaseOrder.status == status)
        
        return query.offset(skip).limit(limit).all()

    def get_purchase_order_by_id(self, po_id: int) -> Optional[PurchaseOrder]:
        return self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    def select_quotation(self, quotation_id: int) -> Optional[Quotation]:
        quotation = self.db.query(Quotation).filter(Quotation.id == quotation_id).first()
        if not quotation:
            return None

        # Desmarcar outras cotações da mesma OC
        self.db.query(Quotation).filter(
            Quotation.purchase_order_id == quotation.purchase_order_id
        ).update({Quotation.is_selected: False})

        # Marcar cotação selecionada
        quotation.is_selected = True
        
        # Atualizar fornecedor da ordem de compra
        purchase_order = quotation.purchase_order
        purchase_order.supplier_id = quotation.supplier_id
        purchase_order.valor_total = quotation.valor_total

        self.db.commit()
        self.db.refresh(quotation)
        return quotation

    # Notas Fiscais
    def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        # Verificar se a ordem de compra existe
        purchase_order = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.id == invoice_data.purchase_order_id
        ).first()
        if not purchase_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de compra não encontrada"
            )

        # Verificar número único da NF
        existing_invoice = self.db.query(Invoice).filter(
            Invoice.numero_nf == invoice_data.numero_nf
        ).first()
        if existing_invoice:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Número da nota fiscal já existe"
            )

        # Criar nota fiscal
        invoice = Invoice(
            purchase_order_id=invoice_data.purchase_order_id,
            numero_nf=invoice_data.numero_nf,
            valor_total=invoice_data.valor_total,
            data_emissao=invoice_data.data_emissao,
            data_vencimento=invoice_data.data_vencimento,
            observacoes=invoice_data.observacoes
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        # Criar itens da nota fiscal
        for item_data in invoice_data.items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                **item_data.dict()
            )
            self.db.add(item)

        self.db.commit()
        return invoice

    def get_invoices(
        self, 
        skip: int = 0, 
        limit: int = 10,
        contract_id: Optional[int] = None
    ) -> List[Invoice]:
        query = self.db.query(Invoice).join(PurchaseOrder)
        
        if contract_id:
            query = query.filter(PurchaseOrder.contract_id == contract_id)
        
        return query.offset(skip).limit(limit).all()

    def pay_invoice(self, invoice_id: int) -> Optional[Invoice]:
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.data_pagamento = func.now()
            self.db.commit()
            self.db.refresh(invoice)
        return invoice