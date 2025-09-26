from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


# Base configuration for all models
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        # Configure JSON serialization
        json_encoders={
            Decimal: float,  # Convert Decimal to float for JSON serialization
        }
    )


class SupplierCreate(BaseSchema):
    nome: str
    cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None


class SupplierResponse(SupplierCreate):
    id: int
    is_approved: bool
    created_at: datetime


class QuotationCreate(BaseSchema):
    supplier_id: int
    valor_total: Decimal
    prazo_entrega_dias: Optional[int] = None
    condicoes_pagamento: Optional[str] = None
    observacoes: Optional[str] = None
    data_cotacao: datetime


class QuotationResponse(QuotationCreate):
    id: int
    purchase_order_id: int
    is_selected: bool
    supplier: SupplierResponse


class PurchaseOrderItemCreate(BaseSchema):
    budget_item_id: Optional[int] = None
    descricao: str
    centro_custo: str
    unidade: Optional[str] = None
    quantidade: Optional[Decimal] = None
    peso: Optional[Decimal] = None
    valor_unitario: Optional[Decimal] = None
    valor_total: Decimal
    # Para serviços
    horas_normais: Optional[Decimal] = None
    horas_extras: Optional[Decimal] = None
    salario: Optional[Decimal] = None


class PurchaseOrderItemResponse(PurchaseOrderItemCreate):
    id: int
    purchase_order_id: int


class PurchaseOrderCreate(BaseSchema):
    contract_id: int
    numero_oc: str
    supplier_id: int
    data_emissao: datetime
    data_entrega_prevista: Optional[datetime] = None
    observacoes: Optional[str] = None
    justificativa_escolha: Optional[str] = None
    items: List[PurchaseOrderItemCreate] = []
    quotations: List[QuotationCreate] = []


class PurchaseOrderResponse(BaseSchema):
    id: int
    contract_id: int
    numero_oc: str
    supplier_id: int
    valor_total: Decimal
    data_emissao: datetime
    data_entrega_prevista: Optional[datetime] = None
    data_entrega_real: Optional[datetime] = None
    status: str
    observacoes: Optional[str] = None
    justificativa_escolha: Optional[str] = None
    criado_por: int
    created_at: datetime
    supplier: SupplierResponse


class PurchaseOrderDetailResponse(PurchaseOrderResponse):
    items: List[PurchaseOrderItemResponse] = []
    quotations: List[QuotationResponse] = []


class InvoiceItemCreate(BaseSchema):
    descricao: str
    centro_custo: str
    unidade: Optional[str] = None
    quantidade: Optional[Decimal] = None
    peso: Optional[Decimal] = None
    valor_unitario: Optional[Decimal] = None
    valor_total: Decimal
    peso_divergente: Optional[Decimal] = None
    valor_divergente: Optional[Decimal] = None
    justificativa_divergencia: Optional[str] = None


class InvoiceItemResponse(InvoiceItemCreate):
    id: int
    invoice_id: int


class InvoiceCreate(BaseSchema):
    purchase_order_id: int
    numero_nf: str
    valor_total: Decimal
    data_emissao: datetime
    data_vencimento: Optional[datetime] = None
    observacoes: Optional[str] = None
    items: List[InvoiceItemCreate] = []


class InvoiceResponse(InvoiceCreate):
    id: int
    data_pagamento: Optional[datetime] = None
    created_at: datetime


class InvoiceDetailResponse(InvoiceResponse):
    items: List[InvoiceItemResponse] = []