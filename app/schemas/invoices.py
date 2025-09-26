from pydantic import BaseModel, validator, ConfigDict
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: float,  # Convert Decimal to float for JSON serialization
        }
    )


class InvoiceItemResponse(BaseSchema):
    id: int
    invoice_id: int
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
    created_at: Optional[datetime] = None


class InvoiceResponse(BaseSchema):
    id: int
    contract_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    numero_nf: str
    fornecedor: Optional[str] = None
    valor_total: Decimal
    data_emissao: datetime
    data_vencimento: Optional[datetime] = None
    data_pagamento: Optional[datetime] = None
    arquivo_original: Optional[str] = None
    observacoes: Optional[str] = None
    created_at: Optional[datetime] = None
    items_count: Optional[int] = None


class InvoiceDetailResponse(InvoiceResponse):
    items: List[InvoiceItemResponse] = []


class InvoiceUploadResponse(BaseSchema):
    success: bool
    message: str
    processed_count: int
    failed_count: int
    invoices: List[InvoiceResponse]
    errors: List[str] = []


class OneDriveUrlRequest(BaseSchema):
    folder_url: str

    @validator('folder_url')
    def validate_onedrive_url(cls, v):
        if not v:
            raise ValueError('URL da pasta é obrigatória')

        # Validações básicas de URL do OneDrive
        onedrive_domains = [
            'onedrive.live.com',
            '1drv.ms',
            'sharepoint.com',
            'office.com'
        ]

        if not any(domain in v.lower() for domain in onedrive_domains):
            raise ValueError('URL deve ser de uma pasta do OneDrive/SharePoint')

        return v


class InvoiceCreate(BaseSchema):
    contract_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    numero_nf: str
    fornecedor: Optional[str] = None
    valor_total: Decimal
    data_emissao: datetime
    data_vencimento: Optional[datetime] = None
    data_pagamento: Optional[datetime] = None
    arquivo_original: Optional[str] = None
    observacoes: Optional[str] = None


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


class InvoiceProcessingError(BaseSchema):
    file_name: str
    error_message: str
    error_type: str


class InvoicesSummary(BaseSchema):
    total_invoices: int
    total_value: float
    recent_invoices: List[InvoiceResponse]