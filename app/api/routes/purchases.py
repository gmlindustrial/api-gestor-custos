from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_suprimentos_user, get_diretoria_user
from app.models.users import User
from app.schemas.purchases import (
    SupplierCreate, SupplierResponse,
    PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderDetailResponse,
    InvoiceCreate, InvoiceResponse, InvoiceDetailResponse,
    QuotationResponse
)
from app.services.purchases import PurchaseService

router = APIRouter()

# Fornecedores
@router.post("/suppliers/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier_data: SupplierCreate,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    return service.create_supplier(supplier_data)


@router.get("/suppliers/", response_model=List[SupplierResponse])
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    approved_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    return service.get_suppliers(skip, limit, approved_only)


@router.patch("/suppliers/{supplier_id}/approve", response_model=SupplierResponse)
async def approve_supplier(
    supplier_id: int,
    current_user: User = Depends(get_diretoria_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    supplier = service.approve_supplier(supplier_id)
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fornecedor não encontrado"
        )
    
    return supplier


# Ordens de Compra
@router.post("/orders/", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_data: PurchaseOrderCreate,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    purchase_order = service.create_purchase_order(po_data, current_user.id)
    return purchase_order


@router.get("/orders/", response_model=List[PurchaseOrderResponse])
async def list_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    contract_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    return service.get_purchase_orders(skip, limit, contract_id, status)


@router.get("/orders/{po_id}", response_model=PurchaseOrderDetailResponse)
async def get_purchase_order(
    po_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    purchase_order = service.get_purchase_order_by_id(po_id)
    
    if not purchase_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de compra não encontrada"
        )
    
    return purchase_order


@router.post("/quotations/{quotation_id}/select", response_model=QuotationResponse)
async def select_quotation(
    quotation_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    quotation = service.select_quotation(quotation_id)
    
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotação não encontrada"
        )
    
    return quotation


# Notas Fiscais
@router.post("/invoices/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    return service.create_invoice(invoice_data)


@router.get("/invoices/", response_model=List[InvoiceResponse])
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    contract_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    return service.get_invoices(skip, limit, contract_id)


@router.patch("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
async def pay_invoice(
    invoice_id: int,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    service = PurchaseService(db)
    invoice = service.pay_invoice(invoice_id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota fiscal não encontrada"
        )
    
    return invoice