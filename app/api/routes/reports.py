from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_diretoria_user
from app.models.users import User, UserRole
from app.schemas.reports import ReportRequest, ReportResponse
from app.services.reports_simple import SimpleReportsService
import os

router = APIRouter()


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Controle de acesso baseado no tipo de relatório
    if request.report_type.value == "analitico":
        # Relatório analítico: apenas Suprimentos e Diretoria
        if current_user.role not in [UserRole.SUPRIMENTOS, UserRole.DIRETORIA, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: Relatório analítico disponível apenas para Suprimentos e Diretoria"
            )
    
    elif request.report_type.value == "sintetico" or request.report_type.value == "conta_corrente":
        # Relatórios sintéticos: todos os perfis podem acessar
        # Clientes só veem dados dos seus contratos (implementar filtro por cliente)
        pass

    service = SimpleReportsService(db)
    
    try:
        result = service.generate_report(request)
        return ReportResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao gerar relatório: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_report(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    file_path = os.path.join("reports", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado"
        )
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@router.get("/analytical/preview")
async def preview_analytical_report(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar permissões
    if current_user.role not in [UserRole.SUPRIMENTOS, UserRole.DIRETORIA, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    service = SimpleReportsService(db)
    
    request = ReportRequest(
        report_type="analitico",
        format="json",
        filters={"contract_id": contract_id}
    )
    
    try:
        result = service.generate_report(request)
        return result["data"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao gerar preview: {str(e)}"
        )


@router.get("/balance/preview")
async def preview_balance_report(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = SimpleReportsService(db)
    
    request = ReportRequest(
        report_type="conta_corrente",
        format="json",
        filters={"contract_id": contract_id}
    )
    
    try:
        result = service.generate_report(request)
        return result["data"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao gerar preview: {str(e)}"
        )