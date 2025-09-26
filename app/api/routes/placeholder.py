"""Endpoints temporários para evitar 404s enquanto o frontend não está totalmente sincronizado"""

from fastapi import APIRouter

router = APIRouter()

# Endpoints temporários que retornam dados vazios ou de exemplo
@router.get("/nf")
async def get_nf():
    return {"nfs": [], "total": 0}

@router.get("/nf/stats")
async def get_nf_stats():
    return {
        "total_nfs": 0,
        "pending_validation": 0,
        "validated": 0,
        "total_value": 0
    }

@router.get("/classification/cost-centers")
async def get_cost_centers():
    return {"cost_centers": [], "total": 0}

@router.get("/classification/rules")
async def get_classification_rules():
    return {"rules": [], "total": 0}

@router.get("/classification/stats")
async def get_classification_stats():
    return {
        "total_items": 0,
        "classified": 0,
        "needs_review": 0,
        "accuracy_score": 0
    }