from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from sqlalchemy import func

from app.core.database import get_db
from app.api.dependencies import get_current_user, get_comercial_user
from app.models.users import User
from app.models.contracts import Contract, BudgetItem, ValorPrevisto
from app.models.purchases import Invoice, PurchaseOrder
from app.schemas.contracts import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractDetailResponse,
    ContractListResponse,
    ValorPrevistoResponse
)
from app.services.nf_service import NotaFiscalService

router = APIRouter()


@router.get("/", response_model=ContractListResponse)
async def list_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    cliente: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todos os contratos"""

    query = db.query(Contract)

    if cliente:
        query = query.filter(Contract.cliente.ilike(f"%{cliente}%"))
    if status_filter:
        query = query.filter(Contract.status == status_filter)

    total = query.count()
    contracts = query.offset(skip).limit(limit).all()

    service = NotaFiscalService(db)
    contract_responses = []

    for contract in contracts:
        valor_realizado = service.calculate_contract_realized_value(contract.id)
        percentual_realizado = (
            (valor_realizado / Decimal(contract.valor_original)) * 100
            if contract.valor_original > 0 else Decimal('0')
        )
        saldo_contrato = Decimal(contract.valor_original) - valor_realizado
        economia_obtida = Decimal(contract.valor_original) * (Decimal(contract.meta_reducao_percentual) / 100)

        safe_name = contract.nome_projeto or "Projeto sem nome"
        safe_client = contract.cliente or "Cliente não informado"
        safe_contract_type = contract.tipo_contrato or "material"
        safe_status = contract.status or "Em Andamento"

        contract_data = {
            "id": contract.id,
            "name": safe_name,
            "client": safe_client,
            "contractType": safe_contract_type,
            "value": Decimal(contract.valor_original),
            "spent": valor_realizado,
            "progress": percentual_realizado,
            "status": safe_status,
            "startDate": contract.data_inicio,
            "endDate": contract.data_fim_real,
            "numero_contrato": contract.numero_contrato,
            "meta_reducao_percentual": contract.meta_reducao_percentual,
            "data_fim_prevista": contract.data_fim_prevista,
            "observacoes": contract.observacoes,
            "criado_por": contract.criado_por,
            "created_at": contract.created_at,
            "updated_at": contract.updated_at,
            "hasBudgetImport": len(contract.budget_items) > 0 if hasattr(contract, 'budget_items') else False
        }
        contract_responses.append(ContractResponse(**contract_data))

    return ContractListResponse(
        contracts=contract_responses,
        total=total,
        page=(skip // limit) + 1,
        per_page=limit
    )


@router.get("/kpis")
async def get_contracts_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter KPIs gerais dos contratos"""

    contracts = db.query(Contract).all()
    if not contracts:
        return {
            "data": {
                "totalValue": Decimal('0'),
                "totalSpent": Decimal('0'),
                "avgProgress": Decimal('0'),
                "activeContracts": 0
            }
        }

    total_value = sum(Decimal(contract.valor_original) for contract in contracts)
    active_contracts = len([c for c in contracts if c.status == "Em Andamento"])

    service = NotaFiscalService(db)
    total_realized = sum(service.calculate_contract_realized_value(contract.id) for contract in contracts)

    avg_progress = (total_realized / total_value) * 100 if total_value > 0 else Decimal('0')

    return {
        "data": {
            "totalValue": total_value,
            "totalSpent": total_realized,
            "avgProgress": avg_progress,
            "activeContracts": active_contracts
        }
    }


@router.get("/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detalhe de um contrato específico"""

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    budget_items = db.query(BudgetItem).filter(BudgetItem.contract_id == contract_id).all()
    valores_previstos = db.query(ValorPrevisto).filter(ValorPrevisto.contract_id == contract_id).all()

    service = NotaFiscalService(db)
    valor_realizado = service.calculate_contract_realized_value(contract.id)
    percentual_realizado = (
        (valor_realizado / Decimal(contract.valor_original)) * 100
        if contract.valor_original > 0 else Decimal('0')
    )

    contract_data = {
        "id": contract.id,
        "name": contract.nome_projeto,
        "client": contract.cliente,
        "contractType": contract.tipo_contrato,
        "value": Decimal(contract.valor_original),
        "spent": valor_realizado,
        "progress": percentual_realizado,
        "status": contract.status,
        "startDate": contract.data_inicio,
        "endDate": contract.data_fim_real,
        "numero_contrato": contract.numero_contrato,
        "meta_reducao_percentual": contract.meta_reducao_percentual,
        "data_fim_prevista": contract.data_fim_prevista,
        "observacoes": contract.observacoes,
        "criado_por": contract.criado_por,
        "created_at": contract.created_at,
        "updated_at": contract.updated_at,
        "hasBudgetImport": len(budget_items) > 0,
        "budget_items": budget_items,
        "valores_previstos": valores_previstos
    }

    return ContractDetailResponse(**contract_data)


@router.post("/", response_model=ContractResponse)
async def create_contract(
    name: str = Form(...),
    client: str = Form(...),
    contractType: str = Form(...),
    startDate: str = Form(...),
    description: str = Form(None),
    qqp_file: UploadFile = File(..., description="Arquivo QQP_Cliente obrigatório"),
    current_user: User = Depends(get_comercial_user),
    db: Session = Depends(get_db)
):
    """Criar novo contrato com arquivo QQP_Cliente obrigatório"""

    from app.services.import_service import DataImportService
    import_service = DataImportService(db)

    try:
        import_result = await import_service.import_budget_from_excel(file=qqp_file, contract_id=None, sheet_name="QQP_Cliente")
        if not import_result['success']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao processar arquivo QQP_Cliente: {import_result['errors']}")
        valor_original = import_result['contract_total_value']
        if not valor_original:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível extrair o valor total do contrato do arquivo QQP_Cliente")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao processar arquivo QQP_Cliente: {str(e)}")

    import time, random
    numero_contrato = f"CONT-{int(time.time())}-{random.randint(1000, 9999)}"
    start_date_obj = datetime.fromisoformat(startDate)

    new_contract = Contract(
        numero_contrato=numero_contrato,
        nome_projeto=name,
        cliente=client,
        tipo_contrato=contractType,
        valor_original=valor_original,
        meta_reducao_percentual=0,
        data_inicio=start_date_obj,
        data_fim_prevista=None,
        observacoes=description,
        criado_por=current_user.id
    )

    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)

    try:
        await qqp_file.seek(0)
        final_import = await import_service.import_budget_from_excel(file=qqp_file, contract_id=new_contract.id, sheet_name="QQP_Cliente")
        if not final_import['success']:
            db.delete(new_contract)
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao salvar itens do orçamento: {final_import['errors']}")
    except Exception as e:
        db.delete(new_contract)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao processar orçamento: {str(e)}")

    valor_realizado = Decimal('0')
    percentual_realizado = Decimal('0')

    contract_response_data = {
        "id": new_contract.id,
        "name": new_contract.nome_projeto,
        "client": new_contract.cliente,
        "contractType": new_contract.tipo_contrato,
        "value": Decimal(new_contract.valor_original),
        "spent": valor_realizado,
        "progress": percentual_realizado,
        "status": new_contract.status,
        "startDate": new_contract.data_inicio,
        "endDate": new_contract.data_fim_real,
        "numero_contrato": new_contract.numero_contrato,
        "meta_reducao_percentual": new_contract.meta_reducao_percentual,
        "data_fim_prevista": new_contract.data_fim_prevista,
        "observacoes": new_contract.observacoes,
        "criado_por": new_contract.criado_por,
        "created_at": new_contract.created_at,
        "updated_at": new_contract.updated_at,
        "hasBudgetImport": True
    }

    return ContractResponse(**contract_response_data)


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdate,
    current_user: User = Depends(get_comercial_user),
    db: Session = Depends(get_db)
):
    """Atualizar contrato"""

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    update_data = contract_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)

    db.commit()
    db.refresh(contract)

    service = NotaFiscalService(db)
    valor_realizado = service.calculate_contract_realized_value(contract.id)
    percentual_realizado = (valor_realizado / Decimal(contract.valor_original)) * 100 if contract.valor_original > 0 else Decimal('0')

    contract_response_data = {
        "id": contract.id,
        "name": contract.nome_projeto,
        "client": contract.cliente,
        "contractType": contract.tipo_contrato,
        "value": Decimal(contract.valor_original),
        "spent": valor_realizado,
        "progress": percentual_realizado,
        "status": contract.status,
        "startDate": contract.data_inicio,
        "endDate": contract.data_fim_real,
        "numero_contrato": contract.numero_contrato,
        "meta_reducao_percentual": contract.meta_reducao_percentual,
        "data_fim_prevista": contract.data_fim_prevista,
        "observacoes": contract.observacoes,
        "criado_por": contract.criado_por,
        "created_at": contract.created_at,
        "updated_at": contract.updated_at,
        "hasBudgetImport": len(contract.budget_items) > 0 if hasattr(contract, 'budget_items') else False
    }

    return ContractResponse(**contract_response_data)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    current_user: User = Depends(get_comercial_user),
    db: Session = Depends(get_db)
):
    """Excluir contrato"""

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    db.query(BudgetItem).filter(BudgetItem.contract_id == contract_id).delete()
    db.delete(contract)
    db.commit()

    return {"message": f"Contrato {contract_id} excluído com sucesso"}
