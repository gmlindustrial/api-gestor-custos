from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum


class ReportType(str, Enum):
    ANALITICO = "analitico"
    SINTETICO = "sintetico"
    CONTA_CORRENTE = "conta_corrente"


class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"


class ReportFilter(BaseModel):
    contract_id: Optional[int] = None
    cliente: Optional[str] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    centro_custo: Optional[str] = None
    fornecedor: Optional[str] = None


class AnalyticalReportItem(BaseModel):
    id: int
    descricao: str
    fornecedor: str
    centro_custo: str
    numero_oc: Optional[str] = None
    numero_nf: Optional[str] = None
    data_emissao: Optional[datetime] = None
    data_entrega: Optional[datetime] = None
    quantidade: Optional[Decimal] = None
    unidade: Optional[str] = None
    peso: Optional[Decimal] = None
    valor_unitario: Optional[Decimal] = None
    valor_total: Decimal
    observacoes: Optional[str] = None


class SyntheticReportItem(BaseModel):
    data: datetime
    numero_oc: str
    numero_nf: str
    fornecedor: str
    valor_total: Decimal


class ContractBalanceReport(BaseModel):
    contract_id: int
    numero_contrato: str
    nome_projeto: str
    cliente: str
    valor_original: Decimal
    valor_realizado: Decimal
    saldo_contrato: Decimal
    percentual_realizado: Decimal
    itens_sinteticos: List[SyntheticReportItem] = []


class AnalyticalReport(BaseModel):
    contract_id: int
    numero_contrato: str
    nome_projeto: str
    periodo_inicio: Optional[datetime] = None
    periodo_fim: Optional[datetime] = None
    total_geral: Decimal
    itens: List[AnalyticalReportItem] = []


class ReportRequest(BaseModel):
    report_type: ReportType
    format: ReportFormat = ReportFormat.JSON
    filters: ReportFilter = ReportFilter()
    include_attachments: bool = False


class ReportResponse(BaseModel):
    report_id: str
    report_type: ReportType
    format: ReportFormat
    generated_at: datetime
    file_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None