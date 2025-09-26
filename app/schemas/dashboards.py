from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime


class KPICard(BaseModel):
    title: str
    value: str
    trend: Optional[str] = None  # "up", "down", "stable"
    percentage_change: Optional[Decimal] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class ChartData(BaseModel):
    labels: List[str]
    datasets: List[Dict[str, Any]]


class SupplierMetric(BaseModel):
    nome: str
    total_compras: Decimal
    numero_ocs: int
    prazo_medio_entrega: Optional[int] = None
    percentual_certificado: Optional[Decimal] = None


class CostCenterMetric(BaseModel):
    centro_custo: str
    valor_previsto: Decimal
    valor_realizado: Decimal
    economia: Decimal
    percentual_economia: Decimal


class ContractProgress(BaseModel):
    contract_id: int
    numero_contrato: str
    nome_projeto: str
    percentual_realizado: Decimal
    percentual_meta: Decimal
    status: str


class SuppliesDashboard(BaseModel):
    # KPIs principais
    total_ordens_compra: int
    total_cotacoes_pendentes: int
    total_fornecedores_aprovados: int
    economia_obtida: Decimal
    percentual_meta_atingida: Decimal
    
    # Cards de KPI
    kpi_cards: List[KPICard]
    
    # Gráficos
    gastos_por_centro_custo: ChartData
    evolucao_mensal_gastos: ChartData
    top_fornecedores: ChartData
    
    # Métricas detalhadas
    fornecedores_desempenho: List[SupplierMetric]
    atrasos_pendentes: List[Dict[str, Any]]
    certificacoes_pendentes: List[Dict[str, Any]]


class ExecutiveDashboard(BaseModel):
    # KPIs estratégicos
    percentual_realizado_total: Decimal
    economia_total: Decimal
    saldo_contratos_total: Decimal
    meta_reducao_atingida: Decimal
    
    # Cards de KPI
    kpi_cards: List[KPICard]
    
    # Gráficos
    previsto_vs_realizado: ChartData
    evolucao_contratos: ChartData
    distribuicao_economia: ChartData
    
    # Progressos dos contratos
    contratos_progresso: List[ContractProgress]
    centros_custo_desempenho: List[CostCenterMetric]
    
    # Alertas e indicadores
    contratos_risco: List[Dict[str, Any]]
    oportunidades_economia: List[Dict[str, Any]]


class DashboardFilters(BaseModel):
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    contract_ids: Optional[List[int]] = None
    cliente: Optional[str] = None
    centro_custo: Optional[str] = None