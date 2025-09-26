from sqlalchemy.orm import Session
from sqlalchemy import func, extract, text, desc
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from app.models.contracts import Contract, BudgetItem
from app.models.purchases import PurchaseOrder, Invoice, Supplier, Quotation
from app.schemas.dashboards import (
    SuppliesDashboard, ExecutiveDashboard, KPICard, ChartData,
    SupplierMetric, CostCenterMetric, ContractProgress, DashboardFilters
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_supplies_dashboard(self, filters: DashboardFilters) -> SuppliesDashboard:
        # Base query with filters
        base_date_filter = self._build_date_filter(filters)
        
        # KPIs principais
        total_ordens_compra = self._count_purchase_orders(filters)
        total_cotacoes_pendentes = self._count_pending_quotations(filters)
        total_fornecedores_aprovados = self._count_approved_suppliers()
        economia_obtida = self._calculate_total_savings(filters)
        
        # Calcular meta atingida (assumindo meta média de 10%)
        meta_total = self._calculate_total_budget(filters) * Decimal('0.10')
        percentual_meta_atingida = (economia_obtida / meta_total * 100) if meta_total > 0 else Decimal('0')

        # KPI Cards
        kpi_cards = [
            KPICard(
                title="Ordens de Compra",
                value=str(total_ordens_compra),
                icon="shopping-cart",
                color="blue"
            ),
            KPICard(
                title="Cotações Pendentes",
                value=str(total_cotacoes_pendentes),
                icon="clock",
                color="orange"
            ),
            KPICard(
                title="Fornecedores Aprovados",
                value=str(total_fornecedores_aprovados),
                icon="users",
                color="green"
            ),
            KPICard(
                title="Economia Obtida",
                value=f"R$ {economia_obtida:,.2f}",
                icon="trending-up",
                color="green"
            ),
            KPICard(
                title="Meta Atingida",
                value=f"{percentual_meta_atingida:.1f}%",
                trend="up" if percentual_meta_atingida >= 100 else "down",
                icon="target",
                color="purple"
            )
        ]

        # Gráficos
        gastos_por_centro_custo = self._get_spending_by_cost_center(filters)
        evolucao_mensal_gastos = self._get_monthly_spending_evolution(filters)
        top_fornecedores = self._get_top_suppliers(filters)
        
        # Métricas detalhadas
        fornecedores_desempenho = self._get_supplier_performance(filters)
        atrasos_pendentes = self._get_pending_delays(filters)
        certificacoes_pendentes = self._get_pending_certifications(filters)

        return SuppliesDashboard(
            total_ordens_compra=total_ordens_compra,
            total_cotacoes_pendentes=total_cotacoes_pendentes,
            total_fornecedores_aprovados=total_fornecedores_aprovados,
            economia_obtida=economia_obtida,
            percentual_meta_atingida=percentual_meta_atingida,
            kpi_cards=kpi_cards,
            gastos_por_centro_custo=gastos_por_centro_custo,
            evolucao_mensal_gastos=evolucao_mensal_gastos,
            top_fornecedores=top_fornecedores,
            fornecedores_desempenho=fornecedores_desempenho,
            atrasos_pendentes=atrasos_pendentes,
            certificacoes_pendentes=certificacoes_pendentes
        )

    def get_executive_dashboard(self, filters: DashboardFilters) -> ExecutiveDashboard:
        # KPIs estratégicos
        percentual_realizado_total = self._calculate_overall_completion_percentage(filters)
        economia_total = self._calculate_total_savings(filters)
        saldo_contratos_total = self._calculate_total_contract_balance(filters)
        meta_reducao_atingida = self._calculate_overall_target_achievement(filters)

        # KPI Cards
        kpi_cards = [
            KPICard(
                title="% Realizado Total",
                value=f"{percentual_realizado_total:.1f}%",
                icon="bar-chart",
                color="blue"
            ),
            KPICard(
                title="Economia Total",
                value=f"R$ {economia_total:,.2f}",
                icon="dollar-sign",
                color="green"
            ),
            KPICard(
                title="Saldo Contratos",
                value=f"R$ {saldo_contratos_total:,.2f}",
                icon="credit-card",
                color="orange"
            ),
            KPICard(
                title="Meta de Redução",
                value=f"{meta_reducao_atingida:.1f}%",
                trend="up" if meta_reducao_atingida >= 100 else "down",
                icon="target",
                color="purple"
            )
        ]

        # Gráficos
        previsto_vs_realizado = self._get_budget_vs_actual(filters)
        evolucao_contratos = self._get_contracts_evolution(filters)
        distribuicao_economia = self._get_savings_distribution(filters)
        
        # Progressos e métricas
        contratos_progresso = self._get_contracts_progress(filters)
        centros_custo_desempenho = self._get_cost_centers_performance(filters)
        contratos_risco = self._identify_at_risk_contracts(filters)
        oportunidades_economia = self._identify_savings_opportunities(filters)

        return ExecutiveDashboard(
            percentual_realizado_total=percentual_realizado_total,
            economia_total=economia_total,
            saldo_contratos_total=saldo_contratos_total,
            meta_reducao_atingida=meta_reducao_atingida,
            kpi_cards=kpi_cards,
            previsto_vs_realizado=previsto_vs_realizado,
            evolucao_contratos=evolucao_contratos,
            distribuicao_economia=distribuicao_economia,
            contratos_progresso=contratos_progresso,
            centros_custo_desempenho=centros_custo_desempenho,
            contratos_risco=contratos_risco,
            oportunidades_economia=oportunidades_economia
        )

    # Métodos auxiliares
    def _build_date_filter(self, filters: DashboardFilters):
        conditions = []
        if filters.data_inicio:
            conditions.append(Invoice.data_emissao >= filters.data_inicio)
        if filters.data_fim:
            conditions.append(Invoice.data_emissao <= filters.data_fim)
        return conditions

    def _count_purchase_orders(self, filters: DashboardFilters) -> int:
        query = self.db.query(PurchaseOrder)
        if filters.contract_ids:
            query = query.filter(PurchaseOrder.contract_id.in_(filters.contract_ids))
        return query.count()

    def _count_pending_quotations(self, filters: DashboardFilters) -> int:
        return self.db.query(Quotation).filter(
            Quotation.is_selected == False
        ).count()

    def _count_approved_suppliers(self) -> int:
        return self.db.query(Supplier).filter(Supplier.is_approved == True).count()

    def _calculate_total_savings(self, filters: DashboardFilters) -> Decimal:
        # Calcula economia como diferença entre previsto e realizado
        query = self.db.query(
            func.sum(BudgetItem.valor_total_previsto).label('previsto'),
            func.sum(Invoice.valor_total).label('realizado')
        ).select_from(Contract).join(BudgetItem).join(PurchaseOrder).join(Invoice)
        
        if filters.contract_ids:
            query = query.filter(Contract.id.in_(filters.contract_ids))
        
        date_filters = self._build_date_filter(filters)
        for condition in date_filters:
            query = query.filter(condition)
        
        result = query.first()
        previsto = result.previsto or Decimal('0')
        realizado = result.realizado or Decimal('0')
        
        return previsto - realizado

    def _calculate_total_budget(self, filters: DashboardFilters) -> Decimal:
        query = self.db.query(func.sum(BudgetItem.valor_total_previsto))
        
        if filters.contract_ids:
            query = query.join(Contract).filter(Contract.id.in_(filters.contract_ids))
        
        return query.scalar() or Decimal('0')

    def _get_spending_by_cost_center(self, filters: DashboardFilters) -> ChartData:
        query = self.db.query(
            Invoice.valor_total,
            func.coalesce(BudgetItem.centro_custo, 'Outros').label('centro_custo')
        ).select_from(Invoice).join(PurchaseOrder).outerjoin(
            BudgetItem, PurchaseOrder.id == BudgetItem.contract_id
        )
        
        date_filters = self._build_date_filter(filters)
        for condition in date_filters:
            query = query.filter(condition)
        
        # Group by cost center
        results = query.all()
        cost_centers = {}
        
        for valor, centro_custo in results:
            if centro_custo not in cost_centers:
                cost_centers[centro_custo] = Decimal('0')
            cost_centers[centro_custo] += valor
        
        return ChartData(
            labels=list(cost_centers.keys()),
            datasets=[{
                'label': 'Gastos por Centro de Custo',
                'data': [float(v) for v in cost_centers.values()],
                'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
            }]
        )

    def _get_monthly_spending_evolution(self, filters: DashboardFilters) -> ChartData:
        query = self.db.query(
            extract('year', Invoice.data_emissao).label('ano'),
            extract('month', Invoice.data_emissao).label('mes'),
            func.sum(Invoice.valor_total).label('total')
        ).group_by('ano', 'mes').order_by('ano', 'mes')
        
        date_filters = self._build_date_filter(filters)
        for condition in date_filters:
            query = query.filter(condition)
        
        results = query.all()
        
        labels = []
        values = []
        
        for ano, mes, total in results:
            labels.append(f"{int(mes):02d}/{int(ano)}")
            values.append(float(total))
        
        return ChartData(
            labels=labels,
            datasets=[{
                'label': 'Evolução Mensal de Gastos',
                'data': values,
                'borderColor': '#36A2EB',
                'backgroundColor': '#36A2EB20'
            }]
        )

    def _get_top_suppliers(self, filters: DashboardFilters) -> ChartData:
        query = self.db.query(
            Supplier.nome,
            func.sum(Invoice.valor_total).label('total')
        ).join(PurchaseOrder).join(Invoice).group_by(
            Supplier.nome
        ).order_by(desc('total')).limit(5)
        
        date_filters = self._build_date_filter(filters)
        for condition in date_filters:
            query = query.filter(condition)
        
        results = query.all()
        
        return ChartData(
            labels=[nome for nome, _ in results],
            datasets=[{
                'label': 'Top Fornecedores por Valor',
                'data': [float(total) for _, total in results],
                'backgroundColor': '#FF6384'
            }]
        )

    def _calculate_overall_completion_percentage(self, filters: DashboardFilters) -> Decimal:
        query = self.db.query(
            func.sum(Contract.valor_original).label('total_contratos'),
            func.sum(Invoice.valor_total).label('total_realizado')
        ).select_from(Contract).outerjoin(PurchaseOrder).outerjoin(Invoice)
        
        if filters.contract_ids:
            query = query.filter(Contract.id.in_(filters.contract_ids))
        
        result = query.first()
        total_contratos = result.total_contratos or Decimal('0')
        total_realizado = result.total_realizado or Decimal('0')
        
        return (total_realizado / total_contratos * 100) if total_contratos > 0 else Decimal('0')

    def _calculate_total_contract_balance(self, filters: DashboardFilters) -> Decimal:
        query = self.db.query(
            func.sum(Contract.valor_original).label('total_contratos'),
            func.sum(Invoice.valor_total).label('total_realizado')
        ).select_from(Contract).outerjoin(PurchaseOrder).outerjoin(Invoice)
        
        if filters.contract_ids:
            query = query.filter(Contract.id.in_(filters.contract_ids))
        
        result = query.first()
        total_contratos = result.total_contratos or Decimal('0')
        total_realizado = result.total_realizado or Decimal('0')
        
        return total_contratos - total_realizado

    def _calculate_overall_target_achievement(self, filters: DashboardFilters) -> Decimal:
        # Calcular o percentual médio de meta atingida
        query = self.db.query(
            Contract.meta_reducao_percentual,
            func.sum(BudgetItem.valor_total_previsto).label('previsto'),
            func.sum(Invoice.valor_total).label('realizado')
        ).select_from(Contract).join(BudgetItem).join(PurchaseOrder).join(Invoice).group_by(
            Contract.id, Contract.meta_reducao_percentual
        )
        
        if filters.contract_ids:
            query = query.filter(Contract.id.in_(filters.contract_ids))
        
        results = query.all()
        total_meta_atingida = Decimal('0')
        contratos_com_meta = 0
        
        for meta, previsto, realizado in results:
            if meta and previsto:
                economia = previsto - realizado
                percentual_economia = (economia / previsto * 100)
                percentual_meta = (percentual_economia / meta * 100) if meta > 0 else Decimal('0')
                total_meta_atingida += percentual_meta
                contratos_com_meta += 1
        
        return (total_meta_atingida / contratos_com_meta) if contratos_com_meta > 0 else Decimal('0')

    def _get_budget_vs_actual(self, filters: DashboardFilters) -> ChartData:
        # Implementar gráfico previsto vs realizado por contrato
        pass

    def _get_contracts_evolution(self, filters: DashboardFilters) -> ChartData:
        # Implementar evolução dos contratos ao longo do tempo
        pass

    def _get_savings_distribution(self, filters: DashboardFilters) -> ChartData:
        # Implementar distribuição de economia por centro de custo
        pass

    def _get_contracts_progress(self, filters: DashboardFilters) -> List[ContractProgress]:
        # Implementar progresso detalhado dos contratos
        return []

    def _get_cost_centers_performance(self, filters: DashboardFilters) -> List[CostCenterMetric]:
        # Implementar desempenho por centro de custo
        return []

    def _get_supplier_performance(self, filters: DashboardFilters) -> List[SupplierMetric]:
        # Implementar métricas de desempenho dos fornecedores
        return []

    def _get_pending_delays(self, filters: DashboardFilters) -> List[Dict[str, Any]]:
        # Implementar lista de atrasos pendentes
        return []

    def _get_pending_certifications(self, filters: DashboardFilters) -> List[Dict[str, Any]]:
        # Implementar lista de certificações pendentes
        return []

    def _identify_at_risk_contracts(self, filters: DashboardFilters) -> List[Dict[str, Any]]:
        # Identificar contratos em risco
        return []

    def _identify_savings_opportunities(self, filters: DashboardFilters) -> List[Dict[str, Any]]:
        # Identificar oportunidades de economia
        return []