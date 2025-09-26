"""Schemas Pydantic para Notas Fiscais"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class NotaFiscalItemBase(BaseModel):
    """Schema base para item de nota fiscal"""
    numero_item: int = Field(..., description="Número sequencial do item na NF")
    codigo_produto: Optional[str] = Field(None, max_length=60, description="Código do produto")
    descricao: str = Field(..., description="Descrição do item")
    ncm: Optional[str] = Field(None, max_length=10, description="Código NCM")
    quantidade: Decimal = Field(..., gt=0, description="Quantidade do item")
    unidade: str = Field(..., max_length=10, description="Unidade de medida")
    valor_unitario: Decimal = Field(..., gt=0, description="Valor unitário")
    valor_total: Decimal = Field(..., gt=0, description="Valor total do item")
    peso_liquido: Optional[Decimal] = Field(None, description="Peso líquido")
    peso_bruto: Optional[Decimal] = Field(None, description="Peso bruto")


class NotaFiscalItemCreate(NotaFiscalItemBase):
    """Schema para criação de item de nota fiscal"""
    centro_custo_id: Optional[int] = Field(None, description="ID do centro de custo")
    item_orcamento_id: Optional[int] = Field(None, description="ID do item do orçamento")
    fonte_classificacao: Optional[str] = Field("auto", max_length=20, description="Fonte da classificação")


class NotaFiscalItemUpdate(BaseModel):
    """Schema para atualização de item de nota fiscal"""
    centro_custo_id: Optional[int] = None
    item_orcamento_id: Optional[int] = None
    score_classificacao: Optional[Decimal] = Field(None, ge=0, le=100)
    fonte_classificacao: Optional[str] = Field(None, max_length=20)
    status_integracao: Optional[str] = Field(None, max_length=20)


class NotaFiscalItem(NotaFiscalItemBase):
    """Schema de retorno para item de nota fiscal"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nota_fiscal_id: int
    centro_custo_id: Optional[int] = None
    centro_custo_nome: Optional[str] = None
    item_orcamento_id: Optional[int] = None
    score_classificacao: Optional[Decimal] = None
    fonte_classificacao: Optional[str] = None
    status_integracao: str
    integrado_em: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class NotaFiscalBase(BaseModel):
    """Schema base para nota fiscal"""
    numero: str = Field(..., max_length=50, description="Número da nota fiscal")
    serie: str = Field(..., max_length=10, description="Série da nota fiscal")
    chave_acesso: Optional[str] = Field(None, max_length=44, description="Chave de acesso NFe")
    cnpj_fornecedor: str = Field(..., max_length=18, description="CNPJ do fornecedor")
    nome_fornecedor: str = Field(..., max_length=255, description="Nome do fornecedor")
    valor_total: Decimal = Field(..., gt=0, description="Valor total da nota fiscal")
    valor_produtos: Optional[Decimal] = Field(None, description="Valor dos produtos")
    valor_impostos: Optional[Decimal] = Field(None, description="Valor dos impostos")
    valor_frete: Optional[Decimal] = Field(None, description="Valor do frete")
    data_emissao: datetime = Field(..., description="Data de emissão da NF")
    data_entrada: Optional[datetime] = Field(None, description="Data de entrada")


class NotaFiscalCreate(NotaFiscalBase):
    """Schema para criação de nota fiscal"""
    pasta_origem: str = Field(..., max_length=255, description="Nome da pasta de origem")
    subpasta: Optional[str] = Field(None, max_length=255, description="Subpasta")
    contrato_id: Optional[int] = Field(None, description="ID do contrato")
    ordem_compra_id: Optional[int] = Field(None, description="ID da ordem de compra")
    observacoes: Optional[str] = None
    itens: Optional[List[NotaFiscalItemCreate]] = Field(default_factory=list)


class NotaFiscalUpdate(BaseModel):
    """Schema para atualização de nota fiscal"""
    contrato_id: Optional[int] = None
    ordem_compra_id: Optional[int] = None
    status_processamento: Optional[str] = Field(None, max_length=50)
    observacoes: Optional[str] = None
    data_entrada: Optional[datetime] = None


class NotaFiscal(NotaFiscalBase):
    """Schema de retorno para nota fiscal"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    pasta_origem: str
    subpasta: Optional[str] = None
    status_processamento: str
    observacoes: Optional[str] = None
    contrato_id: Optional[int] = None
    contrato_nome: Optional[str] = None
    ordem_compra_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_by_n8n_at: Optional[datetime] = None
    itens: List[NotaFiscalItem] = Field(default_factory=list)


class ProcessamentoLogBase(BaseModel):
    """Schema base para log de processamento"""
    pasta_nome: str = Field(..., max_length=255, description="Nome da pasta processada")
    status: str = Field(..., max_length=50, description="Status do processamento")
    quantidade_arquivos: Optional[int] = Field(None, description="Quantidade de arquivos processados")
    quantidade_nfs: Optional[int] = Field(None, description="Quantidade de NFs encontradas")
    mensagem: Optional[str] = None
    detalhes_erro: Optional[str] = None


class ProcessamentoLogCreate(ProcessamentoLogBase):
    """Schema para criação de log de processamento"""
    webhook_chamado_em: datetime = Field(default_factory=datetime.now)


class ProcessamentoLog(ProcessamentoLogBase):
    """Schema de retorno para log de processamento"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    webhook_chamado_em: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProcessFolderRequest(BaseModel):
    """Schema para requisição de processamento de pasta"""
    nome_pasta: str = Field(..., min_length=1, max_length=255, description="Nome da pasta a ser processada")


class ProcessFolderResponse(BaseModel):
    """Schema para resposta de processamento de pasta"""
    success: bool
    message: str
    webhook_status: int
    processing_log_id: int
    n8n_url: str


class NotaFiscalStats(BaseModel):
    """Schema para estatísticas de notas fiscais"""
    total_nfs: int
    pending_validation: int
    validated: int
    rejected: int
    total_value: float
    monthly_stats: List[dict]
    status_distribution: dict


class NotaFiscalListResponse(BaseModel):
    """Schema para resposta de listagem de notas fiscais"""
    nfs: List[dict]
    total: int
    page: int
    per_page: int


class ProcessamentoLogListResponse(BaseModel):
    """Schema para resposta de listagem de logs"""
    logs: List[ProcessamentoLog]
    total: int
    page: int
    per_page: int