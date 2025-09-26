from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_comercial_user, get_suprimentos_user
from app.models.users import User
from app.services.import_service_simple import SimpleDataImportService

router = APIRouter()


@router.post("/validate-file")
async def validate_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Valida formato do arquivo e retorna informações básicas.
    Útil para preview antes do upload real.
    """
    service = SimpleDataImportService(db)
    file_info = await service.validate_file_format(file)
    
    return {
        "valid": file_info["valid"],
        "file_info": file_info
    }


@router.post("/budget/excel")
async def import_budget_from_excel(
    contract_id: int = Form(...),
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    skip_rows: int = Form(0),
    current_user: User = Depends(get_comercial_user),
    db: Session = Depends(get_db)
):
    """
    Importa orçamento previsto (QQP Cliente) de planilha Excel.
    Disponível apenas para usuários do Comercial.
    """
    service = SimpleDataImportService(db)
    
    try:
        result = await service.import_budget_from_excel(
            file=file,
            contract_id=contract_id,
            sheet_name=sheet_name,
            skip_rows=skip_rows
        )
        
        return {
            "message": "Orçamento importado com sucesso",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/invoice/xml")
async def import_invoice_from_xml(
    purchase_order_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Importa nota fiscal de arquivo XML (NF-e).
    Disponível apenas para usuários de Suprimentos.
    """
    service = SimpleDataImportService(db)
    
    try:
        result = await service.import_invoice_from_xml(
            file=file,
            purchase_order_id=purchase_order_id
        )
        
        return {
            "message": "Nota fiscal importada com sucesso",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/invoice/excel")
async def import_invoice_from_excel(
    purchase_order_id: int = Form(...),
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    skip_rows: int = Form(0),
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Importa itens de nota fiscal de planilha Excel.
    Disponível apenas para usuários de Suprimentos.
    """
    service = SimpleDataImportService(db)
    
    try:
        result = await service.import_invoice_from_excel(
            file=file,
            purchase_order_id=purchase_order_id,
            sheet_name=sheet_name,
            skip_rows=skip_rows
        )
        
        return {
            "message": "Itens da nota fiscal importados com sucesso",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/cost-centers/suggestions")
async def get_cost_center_suggestions(
    description: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sugere centro de custo baseado na descrição do item.
    Útil para classificação automática durante importação.
    """
    service = SimpleDataImportService(db)
    suggested_center = service._classify_cost_center(description)
    
    # Buscar centros de custo existentes no banco
    from app.models.cost_centers import CostCenter
    existing_centers = db.query(CostCenter).filter(CostCenter.is_active == True).all()
    
    return {
        "suggested_center": suggested_center,
        "description": description,
        "available_centers": [
            {
                "codigo": center.codigo,
                "nome": center.nome,
                "descricao": center.descricao
            }
            for center in existing_centers
        ]
    }


@router.post("/bulk/invoices")
async def bulk_import_invoices(
    contract_id: int = Form(...),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Importação em lote de múltiplas notas fiscais.
    Aceita diversos formatos (XML, Excel, CSV).
    """
    service = SimpleDataImportService(db)
    results = []
    
    for file in files:
        try:
            # Determinar tipo do arquivo e importar apropriadamente
            if file.filename.endswith('.xml'):
                # Para XML, precisamos associar a uma ordem de compra existente
                # Por simplicidade, vamos buscar a primeira OC do contrato
                from app.models.purchases import PurchaseOrder
                po = db.query(PurchaseOrder).filter(
                    PurchaseOrder.contract_id == contract_id
                ).first()
                
                if not po:
                    results.append({
                        "file": file.filename,
                        "success": False,
                        "error": "Nenhuma ordem de compra encontrada para este contrato"
                    })
                    continue
                
                result = await service.import_invoice_from_xml(file, po.id)
                
            elif file.filename.endswith(('.xlsx', '.xls')):
                # Para Excel, também precisamos de uma ordem de compra
                from app.models.purchases import PurchaseOrder
                po = db.query(PurchaseOrder).filter(
                    PurchaseOrder.contract_id == contract_id
                ).first()
                
                if not po:
                    results.append({
                        "file": file.filename,
                        "success": False,
                        "error": "Nenhuma ordem de compra encontrada para este contrato"
                    })
                    continue
                
                result = await service.import_invoice_from_excel(file, po.id)
            
            else:
                results.append({
                    "file": file.filename,
                    "success": False,
                    "error": "Formato de arquivo não suportado"
                })
                continue
            
            results.append({
                "file": file.filename,
                "success": True,
                "details": result
            })
            
        except Exception as e:
            results.append({
                "file": file.filename,
                "success": False,
                "error": str(e)
            })
    
    successful_imports = sum(1 for r in results if r["success"])
    
    return {
        "message": f"{successful_imports}/{len(files)} arquivos importados com sucesso",
        "results": results
    }