from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_suprimentos_user, get_diretoria_user
from app.models.users import User
from app.schemas.dashboards import SuppliesDashboard, ExecutiveDashboard, DashboardFilters
from app.services.dashboards_simple import SimpleDashboardService

router = APIRouter()


@router.get("/supplies", response_model=SuppliesDashboard)
async def get_supplies_dashboard(
    data_inicio: Optional[datetime] = Query(None, description="Data de início do filtro"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim do filtro"),
    contract_ids: Optional[List[int]] = Query(None, description="IDs dos contratos para filtrar"),
    centro_custo: Optional[str] = Query(None, description="Centro de custo para filtrar"),
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Dashboard específico para a equipe de Suprimentos.
    Mostra métricas relacionadas a compras, cotações, fornecedores e economia.
    """
    filters = DashboardFilters(
        data_inicio=data_inicio,
        data_fim=data_fim,
        contract_ids=contract_ids,
        centro_custo=centro_custo
    )
    
    service = SimpleDashboardService(db)
    return service.get_supplies_dashboard(filters)


@router.get("/executive", response_model=ExecutiveDashboard)
async def get_executive_dashboard(
    data_inicio: Optional[datetime] = Query(None, description="Data de início do filtro"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim do filtro"),
    contract_ids: Optional[List[int]] = Query(None, description="IDs dos contratos para filtrar"),
    cliente: Optional[str] = Query(None, description="Cliente para filtrar"),
    current_user: User = Depends(get_diretoria_user),
    db: Session = Depends(get_db)
):
    """
    Dashboard executivo para a Diretoria.
    Apresenta indicadores estratégicos, economia total, progresso dos contratos
    e oportunidades de otimização.
    """
    filters = DashboardFilters(
        data_inicio=data_inicio,
        data_fim=data_fim,
        contract_ids=contract_ids,
        cliente=cliente
    )
    
    service = SimpleDashboardService(db)
    return service.get_executive_dashboard(filters)


@router.get("/kpis/summary")
async def get_kpis_summary(
    contract_id: Optional[int] = Query(None, description="ID do contrato específico"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resumo rápido dos principais KPIs.
    Disponível para todos os usuários autenticados.
    """
    filters = DashboardFilters(
        contract_ids=[contract_id] if contract_id else None
    )
    
    service = SimpleDashboardService(db)
    
    # Para usuários não-diretoria, retornar apenas métricas básicas
    if current_user.role.value != "diretoria" and current_user.role.value != "admin":
        supplies_dashboard = service.get_supplies_dashboard(filters)
        return {
            "total_ordens_compra": supplies_dashboard.total_ordens_compra,
            "economia_obtida": supplies_dashboard.economia_obtida,
            "fornecedores_aprovados": supplies_dashboard.total_fornecedores_aprovados
        }
    
    # Para diretoria, retornar KPIs estratégicos
    executive_dashboard = service.get_executive_dashboard(filters)
    return {
        "percentual_realizado_total": executive_dashboard.percentual_realizado_total,
        "economia_total": executive_dashboard.economia_total,
        "saldo_contratos_total": executive_dashboard.saldo_contratos_total,
        "meta_reducao_atingida": executive_dashboard.meta_reducao_atingida
    }


@router.get("/contracts/{contract_id}/metrics")
async def get_contract_specific_metrics(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Métricas específicas de um contrato individual.
    Útil para widgets e cards específicos do contrato.
    """
    from app.services.contracts import ContractService
    
    contract_service = ContractService(db)
    contract = contract_service.get_contract_by_id(contract_id)
    
    if not contract:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado"
        )
    
    metrics = contract_service.calculate_contract_metrics(contract_id)
    
    return {
        "contract_id": contract_id,
        "numero_contrato": contract.numero_contrato,
        "nome_projeto": contract.nome_projeto,
        "cliente": contract.cliente,
        "valor_original": contract.valor_original,
        "meta_reducao_percentual": contract.meta_reducao_percentual,
        **metrics
    }


# Additional endpoints for frontend compatibility
@router.get("/kpis")
async def get_dashboard_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    KPIs principais do dashboard - compatível com frontend
    """
    from app.models.contracts import Contract
    from app.services.nf_service import NotaFiscalService

    # Buscar todos os contratos
    contracts = db.query(Contract).all()

    if not contracts:
        return {
            "contractBalance": 0,
            "realizedSavings": 0,
            "reductionTarget": 0,
            "pendingPurchases": 0
        }

    nf_service = NotaFiscalService(db)

    # Calcular valores reais baseados nas NFs validadas
    total_value = sum(float(contract.valor_original) for contract in contracts)
    total_spent = 0

    # Somar valor realizado de todos os contratos
    for contract in contracts:
        contract_spent = float(nf_service.calculate_contract_realized_value(contract.id))
        total_spent += contract_spent

    contract_balance = total_value - total_spent

    # Calcular economia baseada no valor orçado vs realizado
    # Para isso, precisamos dos valores previstos (orçamento detalhado)
    from app.models.contracts import BudgetItem
    budget_total = db.query(func.sum(BudgetItem.valor_total_previsto)).scalar() or 0
    budget_total = float(budget_total)

    # Economia = Orçado - Realizado (quando positivo)
    realized_savings = max(0, budget_total - total_spent) if budget_total > 0 else 0
    realized_savings_percent = (realized_savings / budget_total * 100) if budget_total > 0 else 0

    # Contar compras pendentes (POs não finalizadas)
    from app.models.purchases import PurchaseOrder
    pending_purchases = db.query(PurchaseOrder).filter(
        PurchaseOrder.status.in_(['pending', 'approved', 'processing'])
    ).count()

    return {
        "contractBalance": contract_balance,
        "realizedSavings": realized_savings_percent,  # Retorna como percentual
        "reductionTarget": 15.0,  # Meta de redução padrão
        "pendingPurchases": pending_purchases
    }


@router.get("/active-contracts")
async def get_active_contracts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista de contratos ativos para dashboard
    """
    from app.models.contracts import Contract
    from app.services.nf_service import NotaFiscalService

    # Buscar contratos ativos
    contracts = db.query(Contract).filter(Contract.status == "Em Andamento").limit(5).all()

    nf_service = NotaFiscalService(db)
    result = []

    for contract in contracts:
        # Calcular valores reais baseados nas NFs validadas
        budget = float(contract.valor_original)
        spent = float(nf_service.calculate_contract_realized_value(contract.id))
        progress = (spent / budget) * 100 if budget > 0 else 0

        result.append({
            "id": contract.id,
            "name": contract.nome_projeto,
            "progress": progress,
            "budget": budget,
            "spent": spent,
            "status": contract.status
        })

    return result


@router.get("/activities")
async def get_dashboard_activities(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atividades recentes para dashboard
    """
    from app.models.contracts import Contract

    # Por enquanto, retornar atividades baseadas em contratos criados recentemente
    recent_contracts = db.query(Contract).order_by(Contract.created_at.desc()).limit(limit).all()

    activities = []
    for contract in recent_contracts:
        activities.append({
            "id": contract.id,
            "type": "contract",
            "description": f"Contrato '{contract.nome_projeto}' criado",
            "date": contract.created_at.isoformat() if contract.created_at else None,
            "status": "completed",
            "value": float(contract.valor_original)
        })

    return activities


@router.get("/alerts")
async def get_dashboard_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Alertas do dashboard
    """
    from app.models.contracts import Contract

    alerts = []

    # Buscar contratos com alto valor
    high_value_contracts = db.query(Contract).filter(Contract.valor_original > 1000000).all()

    for contract in high_value_contracts:
        alerts.append({
            "id": contract.id,
            "type": "budget",
            "title": "Contrato de Alto Valor",
            "description": f"Contrato '{contract.nome_projeto}' tem valor elevado: R$ {float(contract.valor_original):,.2f}",
            "priority": "medium",
            "contractId": contract.id,
            "actionUrl": f"/contracts/{contract.id}"
        })

    # Adicionar alerta genérico se não houver outros
    if not alerts:
        alerts.append({
            "id": 1,
            "type": "sync",
            "title": "Sistema Funcionando",
            "description": "Todos os sistemas estão operando normalmente",
            "priority": "low"
        })

    return alerts