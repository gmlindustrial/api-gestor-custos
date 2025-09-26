from pydantic import BaseModel, validator, ConfigDict
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from app.models.contracts import ContractType, ContractStatus


# Base configuration for all models
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        # Configure JSON serialization
        json_encoders={
            Decimal: float,  # Convert Decimal to float for JSON serialization
        }
    )


# Frontend-compatible budget item schema
class BudgetItemCreate(BaseSchema):
    id: str  # codigo_item -> id
    description: str  # descricao -> description
    category: str  # centro_custo -> category
    costCenter: Optional[str] = None  # centro_custo -> costCenter

    # Material/Produto fields
    quantity: Optional[Decimal] = None  # quantidade_prevista -> quantity
    unit: Optional[str] = None  # unidade -> unit
    weight: Optional[Decimal] = None  # peso_previsto -> weight
    unitValue: Optional[Decimal] = None  # valor_unitario_previsto -> unitValue

    # Service fields
    hours: Optional[Decimal] = None  # horas_normais_previstas -> hours
    hourlyRate: Optional[Decimal] = None  # salario_previsto -> hourlyRate
    serviceType: Optional[str] = None

    totalValue: Decimal  # valor_total_previsto -> totalValue

# Backend-compatible budget item schema (for internal use)
class BudgetItemCreateInternal(BaseSchema):
    codigo_item: str
    descricao: str
    centro_custo: str
    unidade: Optional[str] = None
    quantidade_prevista: Optional[Decimal] = None
    peso_previsto: Optional[Decimal] = None
    valor_unitario_previsto: Optional[Decimal] = None
    valor_total_previsto: Decimal
    # Para serviços
    horas_normais_previstas: Optional[Decimal] = None
    horas_extras_previstas: Optional[Decimal] = None
    salario_previsto: Optional[Decimal] = None


class BudgetItemResponse(BudgetItemCreate):
    # Override id to be int instead of str
    id: int  # Database ID
    codigo_item: Optional[str] = None  # Original code for reference
    contract_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Schema para valores previstos (QQP_Cliente)
class ValorPrevistoResponse(BaseSchema):
    id: int
    contract_id: int
    item: str  # Código do item
    servicos: str  # Descrição do serviço
    unidade: Optional[str] = None  # Unidade de medida
    qtd_mensal: Optional[Decimal] = None  # Quantidade mensal
    duracao_meses: Optional[Decimal] = None  # Duração em meses
    preco_total: Decimal  # Preço total
    observacao: Optional[str] = None  # Observações
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Frontend-compatible create schema
class ContractCreate(BaseSchema):
    name: str
    client: str
    contractType: ContractType
    startDate: datetime
    description: Optional[str] = None
    # Não mais incluir value - será extraído do arquivo QQP_Cliente
    # Não mais incluir predictedBudget - será extraído do arquivo

# Backend-compatible create schema (for internal use)
class ContractCreateInternal(BaseSchema):
    numero_contrato: str
    nome_projeto: str
    cliente: str
    tipo_contrato: ContractType
    valor_original: Decimal
    meta_reducao_percentual: Optional[Decimal] = Decimal('0')
    data_inicio: datetime
    data_fim_prevista: Optional[datetime] = None
    observacoes: Optional[str] = None
    budget_items: List[BudgetItemCreate] = []


class ContractUpdate(BaseSchema):
    nome_projeto: Optional[str] = None
    cliente: Optional[str] = None
    valor_original: Optional[Decimal] = None
    meta_reducao_percentual: Optional[Decimal] = None
    status: Optional[ContractStatus] = None
    data_fim_prevista: Optional[datetime] = None
    data_fim_real: Optional[datetime] = None
    observacoes: Optional[str] = None


# Response schema compatible with frontend Contract interface
class ContractResponse(BaseSchema):
    id: int
    name: str  # nome_projeto -> name
    client: str  # cliente -> client
    contractType: ContractType  # tipo_contrato -> contractType
    value: Decimal  # valor_original -> value
    spent: Optional[Decimal] = None  # valor_realizado -> spent
    progress: Optional[Decimal] = None  # percentual_realizado -> progress
    status: ContractStatus
    startDate: datetime  # data_inicio -> startDate
    endDate: Optional[datetime] = None  # data_fim_real -> endDate

    # Campos adicionais do backend (opcionais)
    numero_contrato: Optional[str] = None
    meta_reducao_percentual: Optional[Decimal] = None
    data_fim_prevista: Optional[datetime] = None
    observacoes: Optional[str] = None
    criado_por: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Campos calculados compatíveis com frontend
    hasBudgetImport: Optional[bool] = None


class ContractDetailResponse(ContractResponse):
    budget_items: List[BudgetItemResponse] = []
    valores_previstos: List[ValorPrevistoResponse] = []


class ContractListResponse(BaseSchema):
    contracts: List[ContractResponse]
    total: int
    page: int
    per_page: int