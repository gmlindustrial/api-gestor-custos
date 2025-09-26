"""Serviço de dashboards simplificado"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.models.contracts import Contract, BudgetItem
from app.models.purchases import PurchaseOrder, Invoice, Supplier, Quotation
from app.models.users import User


class SimpleDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_supplies_dashboard(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dashboard para equipe de Suprimentos"""

        filters = filters or {}
        start_date = filters.get('data_inicio')
        end_date = filters.get('data_fim')
        contract_ids = filters.get('contract_ids', [])

        # Query base para purchase orders
        po_query = self.db.query(PurchaseOrder)

        if start_date:
            po_query = po_query.filter(PurchaseOrder.data_emissao >= start_date)
        if end_date:
            po_query = po_query.filter(PurchaseOrder.data_emissao <= end_date)
        if contract_ids:
            po_query = po_query.filter(PurchaseOrder.contract_id.in_(contract_ids))

        purchase_orders = po_query.all()

        # Métricas básicas
        total_orders = len(purchase_orders)
        total_value = sum(float(po.valor_total) for po in purchase_orders)

        # Status das ordens
        orders_by_status = {}
        for po in purchase_orders:
            status = po.status or 'pending'
            orders_by_status[status] = orders_by_status.get(status, 0) + 1

        # Fornecedores aprovados
        approved_suppliers = self.db.query(Supplier).filter(
            Supplier.aprovado == True
        ).count()

        # Cotações pendentes
        pending_quotations = self.db.query(Quotation).filter(
            Quotation.is_selected == None
        ).count()

        # Economia obtida baseada nas NFs validadas
        from app.models.notas_fiscais import NotaFiscal
        from app.services.nf_service import NotaFiscalService

        budget_total = self.db.query(func.sum(BudgetItem.valor_total_previsto)).scalar() or 0

        # Somar valor realizado de NFs validadas
        nf_service = NotaFiscalService(self.db)
        nf_total = self.db.query(func.sum(NotaFiscal.valor_total)).filter(
            NotaFiscal.status_processamento == 'validado'
        ).scalar() or 0

        economy_obtained = float(budget_total) - float(nf_total) if budget_total > nf_total else 0

        # Gastos por centro de custo (últimos 30 dias)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        cost_center_expenses = self.db.query(
            BudgetItem.centro_custo,
            func.sum(BudgetItem.valor_total)
        ).join(
            Contract, BudgetItem.contract_id == Contract.id
        ).filter(
            BudgetItem.created_at >= thirty_days_ago
        ).group_by(BudgetItem.centro_custo).all()

        cost_centers = []
        for center, total in cost_center_expenses:
            cost_centers.append({
                "name": center,
                "value": float(total or 0)
            })

        # Gráfico de tendência mensal (últimos 6 meses)
        monthly_trend = []
        for i in range(6):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = (month_start.replace(month=month_start.month + 1)
                        if month_start.month < 12
                        else month_start.replace(year=month_start.year + 1, month=1))

            monthly_value = self.db.query(func.sum(PurchaseOrder.valor_total)).filter(
                and_(
                    PurchaseOrder.data_emissao >= month_start,
                    PurchaseOrder.data_emissao < month_end
                )
            ).scalar() or 0

            monthly_trend.insert(0, {
                "month": month_start.strftime("%b/%Y"),
                "value": float(monthly_value)
            })

        return {
            "summary": {
                "total_purchase_orders": total_orders,
                "total_value": total_value,
                "approved_suppliers": approved_suppliers,
                "pending_quotations": pending_quotations,
                "economy_obtained": economy_obtained,
                "economy_percentage": (economy_obtained / float(budget_total) * 100) if budget_total > 0 else 0
            },
            "orders_by_status": orders_by_status,
            "cost_center_expenses": cost_centers,
            "monthly_trend": monthly_trend,
            "generated_at": datetime.now().isoformat()
        }

    def get_executive_dashboard(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dashboard executivo para diretoria"""

        filters = filters or {}

        # Contratos ativos
        active_contracts = self.db.query(Contract).filter(
            Contract.status == 'active'
        ).count()

        total_contracts = self.db.query(Contract).count()

        # Valor total dos contratos
        total_contract_value = self.db.query(func.sum(Contract.valor_original)).scalar() or 0

        # Valor realizado total baseado nas NFs validadas
        from app.models.notas_fiscais import NotaFiscal
        from app.services.nf_service import NotaFiscalService

        nf_service = NotaFiscalService(self.db)
        total_realized = 0

        # Somar valor realizado de todos os contratos
        all_contracts = self.db.query(Contract).all()
        for contract in all_contracts:
            total_realized += float(nf_service.calculate_contract_realized_value(contract.id))

        # Percentual de realização geral
        realization_percentage = (total_realized / float(total_contract_value) * 100) if total_contract_value > 0 else 0

        # Economia total obtida baseada no orçamento vs. NFs validadas
        total_budget = self.db.query(func.sum(BudgetItem.valor_total_previsto)).scalar() or 0
        total_economy = float(total_budget) - total_realized if total_budget > total_realized else 0

        # Contratos por status
        contracts_by_status = self.db.query(
            Contract.status,
            func.count(Contract.id)
        ).group_by(Contract.status).all()

        status_distribution = []
        for status, count in contracts_by_status:
            status_distribution.append({
                "status": status,
                "count": count
            })

        # Top 5 contratos por valor
        top_contracts = self.db.query(Contract).order_by(
            Contract.valor_original.desc()
        ).limit(5).all()

        top_contracts_data = []
        for contract in top_contracts:
            top_contracts_data.append({
                "name": contract.nome_projeto,
                "client": contract.cliente,
                "value": float(contract.valor_original or 0),
                "status": contract.status
            })

        # Alertas e riscos (simplificado)
        alerts = []

        # Contratos próximos do fim
        end_date_threshold = datetime.now() + timedelta(days=30)
        expiring_contracts = self.db.query(Contract).filter(
            and_(
                Contract.data_fim_prevista <= end_date_threshold,
                Contract.status == 'Em Andamento'
            )
        ).count()

        if expiring_contracts > 0:
            alerts.append({
                "type": "warning",
                "message": f"{expiring_contracts} contrato(s) vencendo em 30 dias",
                "count": expiring_contracts
            })

        # Ordens de compra pendentes há muito tempo
        old_orders = self.db.query(PurchaseOrder).filter(
            and_(
                PurchaseOrder.status == 'pending',
                PurchaseOrder.data_emissao <= datetime.now() - timedelta(days=15)
            )
        ).count()

        if old_orders > 0:
            alerts.append({
                "type": "error",
                "message": f"{old_orders} ordem(ns) de compra pendente(s) há mais de 15 dias",
                "count": old_orders
            })

        return {
            "summary": {
                "total_contracts": total_contracts,
                "active_contracts": active_contracts,
                "total_contract_value": float(total_contract_value),
                "total_realized": float(total_realized),
                "realization_percentage": realization_percentage,
                "total_economy": total_economy,
                "economy_percentage": (total_economy / float(total_budget) * 100) if total_budget > 0 else 0
            },
            "contracts_by_status": status_distribution,
            "top_contracts": top_contracts_data,
            "alerts": alerts,
            "kpis": {
                "contract_completion_rate": realization_percentage,
                "budget_adherence": ((float(total_budget) - abs(float(total_realized) - float(total_budget))) / float(total_budget) * 100) if total_budget > 0 else 0,
                "supplier_performance": 85.0,  # Mock value
                "cost_efficiency": (total_economy / float(total_budget) * 100) if total_budget > 0 else 0
            },
            "generated_at": datetime.now().isoformat()
        }

    def get_kpis_summary(
        self,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Resumo de KPIs para o período especificado"""

        start_date = datetime.now() - timedelta(days=period_days)

        # KPIs do período
        period_contracts = self.db.query(Contract).filter(
            Contract.created_at >= start_date
        ).count()

        period_orders = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.data_emissao >= start_date
        ).count()

        period_value = self.db.query(func.sum(PurchaseOrder.valor_total)).filter(
            PurchaseOrder.data_emissao >= start_date
        ).scalar() or 0

        # Comparação com período anterior
        previous_start = start_date - timedelta(days=period_days)
        previous_value = self.db.query(func.sum(PurchaseOrder.valor_total)).filter(
            and_(
                PurchaseOrder.data_emissao >= previous_start,
                PurchaseOrder.data_emissao < start_date
            )
        ).scalar() or 0

        value_growth = ((float(period_value) - float(previous_value)) / float(previous_value) * 100) if previous_value > 0 else 0

        return {
            "period_days": period_days,
            "period_contracts": period_contracts,
            "period_orders": period_orders,
            "period_value": float(period_value),
            "value_growth_percentage": value_growth,
            "average_order_value": float(period_value) / period_orders if period_orders > 0 else 0,
            "generated_at": datetime.now().isoformat()
        }