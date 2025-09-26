from fastapi import APIRouter
from app.api.routes import auth, contracts, purchases, reports, dashboards, import_data, nf, classification, invoices

api_router = APIRouter()

# Health check endpoint
@api_router.get("/health")
async def health():
    return {"status": "ok", "message": "GMX - Módulo de Custos API is working"}

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["purchases"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
api_router.include_router(import_data.router, prefix="/import", tags=["import"])
api_router.include_router(nf.router, prefix="/nf", tags=["notas-fiscais"])
api_router.include_router(classification.router, prefix="/classification", tags=["classification"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])