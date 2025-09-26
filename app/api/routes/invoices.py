from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_suprimentos_user
from app.models.users import User
from app.models.purchases import Invoice, InvoiceItem
from app.services.invoice_processing_service import InvoiceProcessingService
from app.schemas.invoices import InvoiceResponse, InvoiceUploadResponse, OneDriveUrlRequest

router = APIRouter()


@router.post("/upload-zip/{contract_id}", response_model=InvoiceUploadResponse)
async def upload_invoices_zip(
    contract_id: int,
    file: UploadFile = File(..., description="Arquivo ZIP contendo notas fiscais"),
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Upload de arquivo ZIP contendo múltiplas notas fiscais.
    Processa automaticamente todos os arquivos XML/PDF dentro do ZIP.
    """

    # Validar se é arquivo ZIP
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser do tipo ZIP"
        )

    # Validar tamanho do arquivo (máximo 100MB)
    file_size = 0
    content = await file.read()
    file_size = len(content)
    await file.seek(0)  # Reset file position

    if file_size > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo ZIP muito grande. Máximo permitido: 100MB"
        )

    try:
        service = InvoiceProcessingService(db)
        result = await service.process_zip_file(
            file=file,
            contract_id=contract_id,
            uploaded_by=current_user.id
        )

        return InvoiceUploadResponse(
            success=True,
            message=f"{result['processed_count']} nota(s) fiscal(is) processada(s) com sucesso",
            processed_count=result['processed_count'],
            failed_count=result['failed_count'],
            invoices=result['invoices'],
            errors=result['errors']
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar arquivo ZIP: {str(e)}"
        )


@router.post("/onedrive-url/{contract_id}", response_model=InvoiceUploadResponse)
async def process_onedrive_url(
    contract_id: int,
    request: OneDriveUrlRequest,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Processa pasta do OneDrive contendo notas fiscais.
    Baixa e processa automaticamente todos os arquivos da pasta.
    """

    try:
        service = InvoiceProcessingService(db)
        result = await service.process_onedrive_folder(
            folder_url=request.folder_url,
            contract_id=contract_id,
            uploaded_by=current_user.id
        )

        return InvoiceUploadResponse(
            success=True,
            message=f"{result['processed_count']} nota(s) fiscal(is) processada(s) com sucesso",
            processed_count=result['processed_count'],
            failed_count=result['failed_count'],
            invoices=result['invoices'],
            errors=result['errors']
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar pasta do OneDrive: {str(e)}"
        )


@router.get("/contract/{contract_id}", response_model=List[InvoiceResponse])
async def get_contract_invoices(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todas as notas fiscais vinculadas a um contrato.
    """

    invoices = db.query(Invoice).filter(Invoice.contract_id == contract_id).all()

    return [
        InvoiceResponse(
            id=invoice.id,
            contract_id=invoice.contract_id,
            purchase_order_id=invoice.purchase_order_id,
            numero_nf=invoice.numero_nf,
            fornecedor=invoice.fornecedor,
            valor_total=invoice.valor_total,
            data_emissao=invoice.data_emissao,
            data_vencimento=invoice.data_vencimento,
            data_pagamento=invoice.data_pagamento,
            arquivo_original=invoice.arquivo_original,
            observacoes=invoice.observacoes,
            created_at=invoice.created_at,
            items_count=len(invoice.items)
        ) for invoice in invoices
    ]


@router.get("/{invoice_id}/items")
async def get_invoice_items(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos os itens de uma nota fiscal específica.
    """

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada"
        )

    return invoice.items


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """
    Remove uma nota fiscal e todos os seus itens.
    """

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada"
        )

    # Deletar itens primeiro (devido ao foreign key)
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()

    # Deletar nota fiscal
    db.delete(invoice)
    db.commit()

    return {"message": f"Nota fiscal {invoice.numero_nf} removida com sucesso"}


@router.get("/contract/{contract_id}/summary")
async def get_contract_invoices_summary(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resumo das notas fiscais de um contrato.
    """

    from sqlalchemy import func

    # Contar e somar valores das notas fiscais
    summary = db.query(
        func.count(Invoice.id).label('total_invoices'),
        func.sum(Invoice.valor_total).label('total_value')
    ).filter(Invoice.contract_id == contract_id).first()

    # Buscar últimas 5 notas fiscais
    recent_invoices = db.query(Invoice).filter(
        Invoice.contract_id == contract_id
    ).order_by(Invoice.created_at.desc()).limit(5).all()

    return {
        "total_invoices": summary.total_invoices or 0,
        "total_value": float(summary.total_value or 0),
        "recent_invoices": [
            {
                "id": invoice.id,
                "numero_nf": invoice.numero_nf,
                "fornecedor": invoice.fornecedor,
                "valor_total": float(invoice.valor_total),
                "data_emissao": invoice.data_emissao,
                "created_at": invoice.created_at
            } for invoice in recent_invoices
        ]
    }