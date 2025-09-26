"""Endpoints para gestão de Notas Fiscais"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import httpx
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_suprimentos_user
from app.models.users import User
from app.models.notas_fiscais import NotaFiscal, NotaFiscalItem, ProcessamentoLog
from app.models.contracts import Contract
from app.services.nf_service import NotaFiscalService
from app.schemas.notas_fiscais import (
    ProcessFolderRequest,
    ProcessFolderResponse,
    NotaFiscalListResponse,
    NotaFiscalStats,
    ProcessamentoLogListResponse,
    NotaFiscalItemUpdate
)

router = APIRouter()


@router.get("/")
async def get_nfs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    supplier: Optional[str] = Query(None),
    contract_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todas as notas fiscais processadas pelo n8n"""

    # Consultar notas fiscais reais do banco
    query = db.query(NotaFiscal)

    # Aplicar filtros
    if status_filter:
        query = query.filter(NotaFiscal.status_processamento.ilike(f"%{status_filter}%"))

    if supplier:
        query = query.filter(NotaFiscal.nome_fornecedor.ilike(f"%{supplier}%"))

    if contract_id:
        query = query.filter(NotaFiscal.contrato_id == contract_id)

    # Contar total antes da paginação
    total = query.count()

    # Aplicar paginação
    nfs = query.offset(skip).limit(limit).all()

    return {
        "nfs": [
            {
                "id": nf.id,
                "number": nf.numero,
                "series": nf.serie,
                "supplier": nf.nome_fornecedor,
                "contract": nf.contrato.nome if nf.contrato else None,
                "contract_id": nf.contrato_id,
                "value": float(nf.valor_total) if nf.valor_total else 0,
                "date": nf.data_emissao.strftime("%Y-%m-%d") if nf.data_emissao else None,
                "status": nf.status_processamento,
                "pasta_origem": nf.pasta_origem,
                "subpasta": nf.subpasta,
                "chave_acesso": nf.chave_acesso,
                "items_count": len(nf.itens) if nf.itens else 0,
                "processed_at": nf.processed_by_n8n_at.isoformat() if nf.processed_by_n8n_at else None
            }
            for nf in nfs
        ],
        "total": total,
        "page": skip // limit + 1,
        "per_page": limit
    }


@router.patch("/item/{item_id}/integrate")
async def integrate_item_to_contract(
    item_id: int,
    integration_data: dict,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Integra um item da NF com o orçamento de um contrato"""

    service = NotaFiscalService(db)

    contrato_id = integration_data.get("contrato_id")
    item_orcamento_id = integration_data.get("item_orcamento_id")

    if not contrato_id or not item_orcamento_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contrato_id e item_orcamento_id são obrigatórios"
        )

    success = service.integrate_item_to_contract(item_id, contrato_id, item_orcamento_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item ou contrato não encontrado"
        )

    return {
        "success": True,
        "message": "Item integrado com sucesso",
        "item_id": item_id,
        "contrato_id": contrato_id,
        "item_orcamento_id": item_orcamento_id
    }


@router.patch("/item/{item_id}")
async def update_item(
    item_id: int,
    item_data: NotaFiscalItemUpdate,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Atualiza um item da nota fiscal"""

    service = NotaFiscalService(db)
    item = service.update_item_nota_fiscal(item_id, item_data)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado"
        )

    return {
        "success": True,
        "message": "Item atualizado com sucesso",
        "item": {
            "id": item.id,
            "centro_custo_id": item.centro_custo_id,
            "item_orcamento_id": item.item_orcamento_id,
            "score_classificacao": float(item.score_classificacao) if item.score_classificacao else None,
            "fonte_classificacao": item.fonte_classificacao,
            "status_integracao": item.status_integracao,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        }
    }


@router.get("/contract/{contract_id}/realized-value")
async def get_contract_realized_value(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calcula valor realizado de um contrato baseado nas NFs validadas"""

    # Verificar se contrato existe
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado"
        )

    service = NotaFiscalService(db)
    valor_realizado = service.calculate_contract_realized_value(contract_id)
    nfs = service.get_nfs_by_contract(contract_id)

    # Calcular estatísticas
    valor_original = float(contract.valor_original)
    percentual_realizado = (float(valor_realizado) / valor_original * 100) if valor_original > 0 else 0
    saldo_restante = valor_original - float(valor_realizado)

    return {
        "contract_id": contract_id,
        "contract_name": contract.nome_projeto,
        "valor_original": valor_original,
        "valor_realizado": float(valor_realizado),
        "percentual_realizado": round(percentual_realizado, 2),
        "saldo_restante": saldo_restante,
        "total_nfs": len(nfs),
        "nfs_validadas": len([nf for nf in nfs if nf.status_processamento == "validado"]),
        "nfs_pendentes": len([nf for nf in nfs if nf.status_processamento == "processado"]),
        "nfs": [
            {
                "id": nf.id,
                "numero": nf.numero,
                "nome_fornecedor": nf.nome_fornecedor,
                "valor_total": float(nf.valor_total),
                "status_processamento": nf.status_processamento,
                "data_emissao": nf.data_emissao.strftime("%Y-%m-%d") if nf.data_emissao else None
            }
            for nf in nfs
        ]
    }


@router.post("/item/{item_id}/classify")
async def classify_item_cost_center(
    item_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Classifica automaticamente um item em centro de custo"""

    item = db.query(NotaFiscalItem).filter(NotaFiscalItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado"
        )

    service = NotaFiscalService(db)
    center_id = service.classify_item_cost_center(item_id, item.descricao)

    if center_id:
        # Recarregar item para obter dados atualizados
        db.refresh(item)

        return {
            "success": True,
            "message": "Item classificado com sucesso",
            "item_id": item_id,
            "centro_custo_id": center_id,
            "score_classificacao": float(item.score_classificacao) if item.score_classificacao else None,
            "fonte_classificacao": item.fonte_classificacao
        }
    else:
        return {
            "success": False,
            "message": "Não foi possível classificar automaticamente este item",
            "item_id": item_id,
            "suggestion": "Classifique manualmente usando o endpoint de atualização"
        }


@router.patch("/{nf_id}/validate")
async def validate_nota_fiscal(
    nf_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Valida uma nota fiscal e integra valores ao contrato"""

    nf = db.query(NotaFiscal).filter(NotaFiscal.id == nf_id).first()
    if not nf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada"
        )

    # Atualizar status para validado
    nf.status_processamento = "validado"
    nf.updated_at = datetime.now()

    # Se tem contrato associado, marcar itens como integrados
    if nf.contrato_id:
        for item in nf.itens:
            if item.status_integracao == "pendente":
                item.status_integracao = "integrado"
                item.integrado_em = datetime.now()
                item.updated_at = datetime.now()

    db.commit()
    db.refresh(nf)

    # Calcular novo valor realizado do contrato se aplicável
    valor_realizado = None
    if nf.contrato_id:
        service = NotaFiscalService(db)
        valor_realizado = float(service.calculate_contract_realized_value(nf.contrato_id))

    return {
        "success": True,
        "message": "Nota fiscal validada com sucesso",
        "nf_id": nf_id,
        "status": nf.status_processamento,
        "contrato_id": nf.contrato_id,
        "valor_realizado_contrato": valor_realizado,
        "validated_by": current_user.full_name,
        "validated_at": datetime.now().isoformat()
    }


@router.get("/stats")
async def get_nf_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Estatísticas das notas fiscais processadas"""

    from sqlalchemy import func, extract

    # Estatísticas básicas
    total_nfs = db.query(NotaFiscal).count()

    # Distribuição por status
    status_counts = db.query(
        NotaFiscal.status_processamento,
        func.count(NotaFiscal.id).label('count')
    ).group_by(NotaFiscal.status_processamento).all()

    status_distribution = {status: count for status, count in status_counts}

    # Valor total
    total_value_result = db.query(func.sum(NotaFiscal.valor_total)).scalar()
    total_value = float(total_value_result) if total_value_result else 0

    # Estatísticas mensais dos últimos 6 meses
    monthly_stats = db.query(
        extract('month', NotaFiscal.data_emissao).label('month'),
        extract('year', NotaFiscal.data_emissao).label('year'),
        func.count(NotaFiscal.id).label('count'),
        func.sum(NotaFiscal.valor_total).label('value')
    ).filter(
        NotaFiscal.data_emissao.isnot(None)
    ).group_by(
        extract('month', NotaFiscal.data_emissao),
        extract('year', NotaFiscal.data_emissao)
    ).order_by(
        extract('year', NotaFiscal.data_emissao).desc(),
        extract('month', NotaFiscal.data_emissao).desc()
    ).limit(6).all()

    # Converter nomes dos meses
    month_names = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }

    monthly_data = []
    for month, year, count, value in monthly_stats:
        monthly_data.append({
            "month": month_names.get(int(month), f"Mês {month}"),
            "year": int(year),
            "count": count,
            "value": float(value) if value else 0
        })

    return {
        "total_nfs": total_nfs,
        "pending_validation": status_distribution.get("processado", 0),
        "validated": status_distribution.get("validado", 0),
        "rejected": status_distribution.get("erro", 0),
        "total_value": total_value,
        "monthly_stats": monthly_data,
        "status_distribution": status_distribution
    }


@router.get("/{nf_id}")
async def get_nf(
    nf_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detalhe de uma nota fiscal específica com seus itens"""

    nf = db.query(NotaFiscal).filter(NotaFiscal.id == nf_id).first()
    if not nf:
        raise HTTPException(status_code=404, detail="Nota fiscal não encontrada")

    return {
        "id": nf.id,
        "number": nf.numero,
        "series": nf.serie,
        "chave_acesso": nf.chave_acesso,
        "supplier": nf.nome_fornecedor,
        "cnpj_fornecedor": nf.cnpj_fornecedor,
        "contract": nf.contrato.nome if nf.contrato else None,
        "contract_id": nf.contrato_id,
        "value": float(nf.valor_total) if nf.valor_total else 0,
        "valor_produtos": float(nf.valor_produtos) if nf.valor_produtos else 0,
        "valor_impostos": float(nf.valor_impostos) if nf.valor_impostos else 0,
        "valor_frete": float(nf.valor_frete) if nf.valor_frete else 0,
        "date": nf.data_emissao.strftime("%Y-%m-%d") if nf.data_emissao else None,
        "data_entrada": nf.data_entrada.strftime("%Y-%m-%d") if nf.data_entrada else None,
        "status": nf.status_processamento,
        "pasta_origem": nf.pasta_origem,
        "subpasta": nf.subpasta,
        "observacoes": nf.observacoes,
        "ordem_compra_id": nf.ordem_compra_id,
        "processed_at": nf.processed_by_n8n_at.isoformat() if nf.processed_by_n8n_at else None,
        "created_at": nf.created_at.isoformat() if nf.created_at else None,
        "items": [
            {
                "id": item.id,
                "numero_item": item.numero_item,
                "codigo_produto": item.codigo_produto,
                "description": item.descricao,
                "quantity": float(item.quantidade) if item.quantidade else 0,
                "unitValue": float(item.valor_unitario) if item.valor_unitario else 0,
                "totalValue": float(item.valor_total) if item.valor_total else 0,
                "unit": item.unidade,
                "peso_liquido": float(item.peso_liquido) if item.peso_liquido else None,
                "peso_bruto": float(item.peso_bruto) if item.peso_bruto else None,
                "ncm": item.ncm,
                "centro_custo_id": item.centro_custo_id,
                "centro_custo": item.centro_custo.nome if item.centro_custo else None,
                "item_orcamento_id": item.item_orcamento_id,
                "classificationScore": float(item.score_classificacao) if item.score_classificacao else None,
                "classificationSource": item.fonte_classificacao,
                "status_integracao": item.status_integracao,
                "integrado_em": item.integrado_em.isoformat() if item.integrado_em else None
            }
            for item in nf.itens
        ] if nf.itens else []
    }


@router.post("/")
async def create_nf(
    nf_data: dict,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Criar nova nota fiscal"""

    # Mock response
    return {
        "id": 999,
        "number": nf_data.get("number", "NEW123"),
        "series": nf_data.get("series", "001"),
        "supplier": nf_data.get("supplier", "Novo Fornecedor"),
        "value": nf_data.get("value", 0),
        "date": datetime.now().isoformat(),
        "status": "Pendente",
        "message": "Nota fiscal criada com sucesso"
    }


@router.put("/{nf_id}")
async def update_nf(
    nf_id: int,
    nf_data: dict,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Atualizar nota fiscal"""

    return {
        "id": nf_id,
        "message": "Nota fiscal atualizada com sucesso",
        "updated_fields": list(nf_data.keys())
    }


@router.patch("/{nf_id}/validate")
async def validate_nf(
    nf_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Validar nota fiscal"""

    return {
        "id": nf_id,
        "status": "Validada",
        "validated_by": current_user.full_name,
        "validated_at": datetime.now().isoformat(),
        "message": "Nota fiscal validada com sucesso"
    }


@router.patch("/{nf_id}/reject")
async def reject_nf(
    nf_id: int,
    reason: str,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Rejeitar nota fiscal"""

    return {
        "id": nf_id,
        "status": "Rejeitada",
        "rejected_by": current_user.full_name,
        "rejected_at": datetime.now().isoformat(),
        "reason": reason,
        "message": "Nota fiscal rejeitada"
    }


@router.post("/import")
async def import_nf(
    file: UploadFile = File(...),
    contract_id: Optional[int] = None,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Importar nota fiscal de arquivo XML"""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo não fornecido")

    if not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Apenas arquivos XML são aceitos")

    # Mock import process
    return {
        "success": True,
        "message": f"Arquivo {file.filename} importado com sucesso",
        "nf": {
            "id": 998,
            "number": "IMPORTED001",
            "series": "001",
            "supplier": "Fornecedor Importado",
            "value": 12500.00,
            "items": 5,
            "contract_id": contract_id
        }
    }


@router.delete("/{nf_id}")
async def delete_nf(
    nf_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Excluir nota fiscal"""

    return {
        "message": f"Nota fiscal {nf_id} excluída com sucesso"
    }


@router.post("/process-folder", response_model=ProcessFolderResponse)
async def process_folder(
    folder_data: ProcessFolderRequest,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para processar pasta de notas fiscais via n8n
    Recebe nome da pasta e chama webhook do n8n para processamento
    """

    folder_name = folder_data.nome_pasta
    if not folder_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome da pasta é obrigatório"
        )

    # Registrar log de processamento iniciado
    processing_log = ProcessamentoLog(
        pasta_nome=folder_name,
        webhook_chamado_em=datetime.now(),
        status="iniciado",
        mensagem="Webhook n8n chamado para processar pasta"
    )
    db.add(processing_log)
    db.commit()
    db.refresh(processing_log)

    try:
        # Chamar webhook do n8n
        n8n_webhook_url = f"https://n8n.gmxindustrial.com.br/webhook/nome_pasta/{folder_name}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(n8n_webhook_url, json={
                "nome_pasta": folder_name,
                "user_id": current_user.id,
                "user_name": current_user.full_name,
                "timestamp": datetime.now().isoformat()
            })

        # Atualizar log com sucesso
        processing_log.status = "webhook_enviado"
        processing_log.mensagem = f"Webhook enviado com sucesso. Status: {response.status_code}"
        db.commit()

        return {
            "success": True,
            "message": f"Processamento da pasta '{folder_name}' iniciado com sucesso",
            "webhook_status": response.status_code,
            "processing_log_id": processing_log.id,
            "n8n_url": n8n_webhook_url
        }

    except httpx.TimeoutException:
        # Atualizar log com erro de timeout
        processing_log.status = "erro"
        processing_log.detalhes_erro = "Timeout ao chamar webhook n8n"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Timeout ao chamar webhook n8n. Tente novamente."
        )

    except httpx.RequestError as e:
        # Atualizar log com erro de conexão
        processing_log.status = "erro"
        processing_log.detalhes_erro = f"Erro de conexão: {str(e)}"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro ao conectar com n8n: {str(e)}"
        )

    except Exception as e:
        # Atualizar log com erro geral
        processing_log.status = "erro"
        processing_log.detalhes_erro = f"Erro inesperado: {str(e)}"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )


@router.get("/processing-logs")
async def get_processing_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista logs de processamento das pastas"""

    logs = db.query(ProcessamentoLog).offset(skip).limit(limit).all()
    total = db.query(ProcessamentoLog).count()

    return {
        "logs": [
            {
                "id": log.id,
                "pasta_nome": log.pasta_nome,
                "webhook_chamado_em": log.webhook_chamado_em,
                "status": log.status,
                "quantidade_arquivos": log.quantidade_arquivos,
                "quantidade_nfs": log.quantidade_nfs,
                "mensagem": log.mensagem,
                "detalhes_erro": log.detalhes_erro,
                "created_at": log.created_at
            }
            for log in logs
        ],
        "total": total,
        "page": skip // limit + 1,
        "per_page": limit
    }


@router.patch("/item/{item_id}/integrate")
async def integrate_item_to_contract(
    item_id: int,
    integration_data: dict,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Integra um item da NF com o orçamento de um contrato"""

    service = NotaFiscalService(db)

    contrato_id = integration_data.get("contrato_id")
    item_orcamento_id = integration_data.get("item_orcamento_id")

    if not contrato_id or not item_orcamento_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contrato_id e item_orcamento_id são obrigatórios"
        )

    success = service.integrate_item_to_contract(item_id, contrato_id, item_orcamento_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item ou contrato não encontrado"
        )

    return {
        "success": True,
        "message": "Item integrado com sucesso",
        "item_id": item_id,
        "contrato_id": contrato_id,
        "item_orcamento_id": item_orcamento_id
    }


@router.patch("/item/{item_id}")
async def update_item(
    item_id: int,
    item_data: NotaFiscalItemUpdate,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Atualiza um item da nota fiscal"""

    service = NotaFiscalService(db)
    item = service.update_item_nota_fiscal(item_id, item_data)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado"
        )

    return {
        "success": True,
        "message": "Item atualizado com sucesso",
        "item": {
            "id": item.id,
            "centro_custo_id": item.centro_custo_id,
            "item_orcamento_id": item.item_orcamento_id,
            "score_classificacao": float(item.score_classificacao) if item.score_classificacao else None,
            "fonte_classificacao": item.fonte_classificacao,
            "status_integracao": item.status_integracao,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        }
    }


@router.get("/contract/{contract_id}/realized-value")
async def get_contract_realized_value(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calcula valor realizado de um contrato baseado nas NFs validadas"""

    # Verificar se contrato existe
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado"
        )

    service = NotaFiscalService(db)
    valor_realizado = service.calculate_contract_realized_value(contract_id)
    nfs = service.get_nfs_by_contract(contract_id)

    # Calcular estatísticas
    valor_original = float(contract.valor_original)
    percentual_realizado = (float(valor_realizado) / valor_original * 100) if valor_original > 0 else 0
    saldo_restante = valor_original - float(valor_realizado)

    return {
        "contract_id": contract_id,
        "contract_name": contract.nome_projeto,
        "valor_original": valor_original,
        "valor_realizado": float(valor_realizado),
        "percentual_realizado": round(percentual_realizado, 2),
        "saldo_restante": saldo_restante,
        "total_nfs": len(nfs),
        "nfs_validadas": len([nf for nf in nfs if nf.status_processamento == "validado"]),
        "nfs_pendentes": len([nf for nf in nfs if nf.status_processamento == "processado"]),
        "nfs": [
            {
                "id": nf.id,
                "numero": nf.numero,
                "nome_fornecedor": nf.nome_fornecedor,
                "valor_total": float(nf.valor_total),
                "status_processamento": nf.status_processamento,
                "data_emissao": nf.data_emissao.strftime("%Y-%m-%d") if nf.data_emissao else None
            }
            for nf in nfs
        ]
    }


@router.post("/item/{item_id}/classify")
async def classify_item_cost_center(
    item_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Classifica automaticamente um item em centro de custo"""

    item = db.query(NotaFiscalItem).filter(NotaFiscalItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado"
        )

    service = NotaFiscalService(db)
    center_id = service.classify_item_cost_center(item_id, item.descricao)

    if center_id:
        # Recarregar item para obter dados atualizados
        db.refresh(item)

        return {
            "success": True,
            "message": "Item classificado com sucesso",
            "item_id": item_id,
            "centro_custo_id": center_id,
            "score_classificacao": float(item.score_classificacao) if item.score_classificacao else None,
            "fonte_classificacao": item.fonte_classificacao
        }
    else:
        return {
            "success": False,
            "message": "Não foi possível classificar automaticamente este item",
            "item_id": item_id,
            "suggestion": "Classifique manualmente usando o endpoint de atualização"
        }


@router.patch("/{nf_id}/validate")
async def validate_nota_fiscal(
    nf_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Valida uma nota fiscal e integra valores ao contrato"""

    nf = db.query(NotaFiscal).filter(NotaFiscal.id == nf_id).first()
    if not nf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada"
        )

    # Atualizar status para validado
    nf.status_processamento = "validado"
    nf.updated_at = datetime.now()

    # Se tem contrato associado, marcar itens como integrados
    if nf.contrato_id:
        for item in nf.itens:
            if item.status_integracao == "pendente":
                item.status_integracao = "integrado"
                item.integrado_em = datetime.now()
                item.updated_at = datetime.now()

    db.commit()
    db.refresh(nf)

    # Calcular novo valor realizado do contrato se aplicável
    valor_realizado = None
    if nf.contrato_id:
        service = NotaFiscalService(db)
        valor_realizado = float(service.calculate_contract_realized_value(nf.contrato_id))

    return {
        "success": True,
        "message": "Nota fiscal validada com sucesso",
        "nf_id": nf_id,
        "status": nf.status_processamento,
        "contrato_id": nf.contrato_id,
        "valor_realizado_contrato": valor_realizado,
        "validated_by": current_user.full_name,
        "validated_at": datetime.now().isoformat()
    }


@router.get("/by-folder/{folder_name}")
async def get_nfs_by_folder(
    folder_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista notas fiscais por pasta (subpasta)"""

    query = db.query(NotaFiscal).filter(NotaFiscal.pasta_origem == folder_name)

    total = query.count()
    nfs = query.offset(skip).limit(limit).all()

    return {
        "folder_name": folder_name,
        "nfs": [
            {
                "id": nf.id,
                "numero": nf.numero,
                "serie": nf.serie,
                "nome_fornecedor": nf.nome_fornecedor,
                "valor_total": float(nf.valor_total),
                "data_emissao": nf.data_emissao,
                "subpasta": nf.subpasta,
                "status_processamento": nf.status_processamento,
                "contrato_id": nf.contrato_id,
                "itens_count": len(nf.itens) if nf.itens else 0
            }
            for nf in nfs
        ],
        "total": total,
        "page": skip // limit + 1,
        "per_page": limit
    }


@router.patch("/item/{item_id}/integrate")
async def integrate_item_to_contract(
    item_id: int,
    integration_data: dict,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Integra um item da NF com o orçamento de um contrato"""

    service = NotaFiscalService(db)

    contrato_id = integration_data.get("contrato_id")
    item_orcamento_id = integration_data.get("item_orcamento_id")

    if not contrato_id or not item_orcamento_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contrato_id e item_orcamento_id são obrigatórios"
        )

    success = service.integrate_item_to_contract(item_id, contrato_id, item_orcamento_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item ou contrato não encontrado"
        )

    return {
        "success": True,
        "message": "Item integrado com sucesso",
        "item_id": item_id,
        "contrato_id": contrato_id,
        "item_orcamento_id": item_orcamento_id
    }


@router.patch("/item/{item_id}")
async def update_item(
    item_id: int,
    item_data: NotaFiscalItemUpdate,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Atualiza um item da nota fiscal"""

    service = NotaFiscalService(db)
    item = service.update_item_nota_fiscal(item_id, item_data)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado"
        )

    return {
        "success": True,
        "message": "Item atualizado com sucesso",
        "item": {
            "id": item.id,
            "centro_custo_id": item.centro_custo_id,
            "item_orcamento_id": item.item_orcamento_id,
            "score_classificacao": float(item.score_classificacao) if item.score_classificacao else None,
            "fonte_classificacao": item.fonte_classificacao,
            "status_integracao": item.status_integracao,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        }
    }


@router.get("/contract/{contract_id}/realized-value")
async def get_contract_realized_value(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calcula valor realizado de um contrato baseado nas NFs validadas"""

    # Verificar se contrato existe
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado"
        )

    service = NotaFiscalService(db)
    valor_realizado = service.calculate_contract_realized_value(contract_id)
    nfs = service.get_nfs_by_contract(contract_id)

    # Calcular estatísticas
    valor_original = float(contract.valor_original)
    percentual_realizado = (float(valor_realizado) / valor_original * 100) if valor_original > 0 else 0
    saldo_restante = valor_original - float(valor_realizado)

    return {
        "contract_id": contract_id,
        "contract_name": contract.nome_projeto,
        "valor_original": valor_original,
        "valor_realizado": float(valor_realizado),
        "percentual_realizado": round(percentual_realizado, 2),
        "saldo_restante": saldo_restante,
        "total_nfs": len(nfs),
        "nfs_validadas": len([nf for nf in nfs if nf.status_processamento == "validado"]),
        "nfs_pendentes": len([nf for nf in nfs if nf.status_processamento == "processado"]),
        "nfs": [
            {
                "id": nf.id,
                "numero": nf.numero,
                "nome_fornecedor": nf.nome_fornecedor,
                "valor_total": float(nf.valor_total),
                "status_processamento": nf.status_processamento,
                "data_emissao": nf.data_emissao.strftime("%Y-%m-%d") if nf.data_emissao else None
            }
            for nf in nfs
        ]
    }


@router.post("/item/{item_id}/classify")
async def classify_item_cost_center(
    item_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Classifica automaticamente um item em centro de custo"""

    item = db.query(NotaFiscalItem).filter(NotaFiscalItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado"
        )

    service = NotaFiscalService(db)
    center_id = service.classify_item_cost_center(item_id, item.descricao)

    if center_id:
        # Recarregar item para obter dados atualizados
        db.refresh(item)

        return {
            "success": True,
            "message": "Item classificado com sucesso",
            "item_id": item_id,
            "centro_custo_id": center_id,
            "score_classificacao": float(item.score_classificacao) if item.score_classificacao else None,
            "fonte_classificacao": item.fonte_classificacao
        }
    else:
        return {
            "success": False,
            "message": "Não foi possível classificar automaticamente este item",
            "item_id": item_id,
            "suggestion": "Classifique manualmente usando o endpoint de atualização"
        }


@router.patch("/{nf_id}/validate")
async def validate_nota_fiscal(
    nf_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Valida uma nota fiscal e integra valores ao contrato"""

    nf = db.query(NotaFiscal).filter(NotaFiscal.id == nf_id).first()
    if not nf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada"
        )

    # Atualizar status para validado
    nf.status_processamento = "validado"
    nf.updated_at = datetime.now()

    # Se tem contrato associado, marcar itens como integrados
    if nf.contrato_id:
        for item in nf.itens:
            if item.status_integracao == "pendente":
                item.status_integracao = "integrado"
                item.integrado_em = datetime.now()
                item.updated_at = datetime.now()

    db.commit()
    db.refresh(nf)

    # Calcular novo valor realizado do contrato se aplicável
    valor_realizado = None
    if nf.contrato_id:
        service = NotaFiscalService(db)
        valor_realizado = float(service.calculate_contract_realized_value(nf.contrato_id))

    return {
        "success": True,
        "message": "Nota fiscal validada com sucesso",
        "nf_id": nf_id,
        "status": nf.status_processamento,
        "contrato_id": nf.contrato_id,
        "valor_realizado_contrato": valor_realizado,
        "validated_by": current_user.full_name,
        "validated_at": datetime.now().isoformat()
    }