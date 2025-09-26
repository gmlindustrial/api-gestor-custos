"""Endpoints para sistema de classificação de custos"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_suprimentos_user, get_admin_user
from app.models.users import User

router = APIRouter()


@router.get("/cost-centers")
async def get_cost_centers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todos os centros de custo"""

    mock_cost_centers = [
        {
            "id": "materia_prima",
            "name": "Matéria-prima",
            "description": "Materiais básicos para construção",
            "category": "material",
            "keywords": ["cimento", "areia", "brita", "cal", "ferro", "vergalhão"],
            "color": "#3B82F6",
            "active": True,
            "budget": {
                "allocated": 150000.00,
                "consumed": 87500.50,
                "remaining": 62499.50
            },
            "createdAt": "2024-01-15T10:00:00Z"
        },
        {
            "id": "mao_obra",
            "name": "Mão-de-obra",
            "description": "Custos relacionados à mão de obra",
            "category": "labor",
            "keywords": ["pedreiro", "servente", "eletricista", "encanador", "pintor"],
            "color": "#10B981",
            "active": True,
            "budget": {
                "allocated": 200000.00,
                "consumed": 125000.00,
                "remaining": 75000.00
            },
            "createdAt": "2024-01-15T10:00:00Z"
        },
        {
            "id": "equipamentos",
            "name": "Equipamentos",
            "description": "Aluguel e compra de equipamentos",
            "category": "equipment",
            "keywords": ["betoneira", "andaime", "guincho", "compressor"],
            "color": "#F59E0B",
            "active": True,
            "budget": {
                "allocated": 80000.00,
                "consumed": 45200.30,
                "remaining": 34799.70
            },
            "createdAt": "2024-01-15T10:00:00Z"
        },
        {
            "id": "servicos",
            "name": "Serviços",
            "description": "Serviços terceirizados",
            "category": "service",
            "keywords": ["consultoria", "projeto", "licenciamento", "transporte"],
            "color": "#8B5CF6",
            "active": True,
            "budget": {
                "allocated": 60000.00,
                "consumed": 18750.00,
                "remaining": 41250.00
            },
            "createdAt": "2024-01-15T10:00:00Z"
        }
    ]

    if active_only:
        mock_cost_centers = [cc for cc in mock_cost_centers if cc["active"]]

    total = len(mock_cost_centers)
    start = skip
    end = skip + limit
    paginated_centers = mock_cost_centers[start:end]

    return {
        "cost_centers": paginated_centers,
        "total": total,
        "page": skip // limit + 1,
        "per_page": limit
    }


@router.post("/cost-centers")
async def create_cost_center(
    cost_center_data: dict,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Criar novo centro de custo"""

    return {
        "id": f"cc_{datetime.now().timestamp()}",
        "name": cost_center_data.get("name"),
        "description": cost_center_data.get("description"),
        "category": cost_center_data.get("category"),
        "keywords": cost_center_data.get("keywords", []),
        "color": cost_center_data.get("color", "#6B7280"),
        "active": True,
        "budget": {
            "allocated": cost_center_data.get("budget", 0),
            "consumed": 0,
            "remaining": cost_center_data.get("budget", 0)
        },
        "createdAt": datetime.now().isoformat(),
        "message": "Centro de custo criado com sucesso"
    }


@router.get("/rules")
async def get_classification_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista todas as regras de classificação"""

    mock_rules = [
        {
            "id": "rule_001",
            "name": "Materiais Cimentícios",
            "costCenterId": "materia_prima",
            "conditions": [
                {
                    "field": "description",
                    "operator": "contains",
                    "value": "cimento",
                    "caseSensitive": False
                }
            ],
            "priority": 10,
            "active": True,
            "hitCount": 45,
            "successRate": 95.5,
            "createdAt": "2024-01-15T10:00:00Z",
            "updatedAt": "2024-03-01T14:30:00Z"
        },
        {
            "id": "rule_002",
            "name": "Serviços de Mão de Obra",
            "costCenterId": "mao_obra",
            "conditions": [
                {
                    "field": "description",
                    "operator": "contains",
                    "value": "mão de obra",
                    "caseSensitive": False
                },
                {
                    "field": "description",
                    "operator": "contains",
                    "value": "serviço",
                    "caseSensitive": False
                }
            ],
            "priority": 8,
            "active": True,
            "hitCount": 23,
            "successRate": 87.2,
            "createdAt": "2024-01-20T09:15:00Z",
            "updatedAt": "2024-02-15T11:45:00Z"
        }
    ]

    if active_only:
        mock_rules = [rule for rule in mock_rules if rule["active"]]

    total = len(mock_rules)
    start = skip
    end = skip + limit
    paginated_rules = mock_rules[start:end]

    return {
        "rules": paginated_rules,
        "total": total,
        "page": skip // limit + 1,
        "per_page": limit
    }


@router.post("/rules")
async def create_classification_rule(
    rule_data: dict,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Criar nova regra de classificação"""

    return {
        "id": f"rule_{datetime.now().timestamp()}",
        "name": rule_data.get("name"),
        "costCenterId": rule_data.get("costCenterId"),
        "conditions": rule_data.get("conditions", []),
        "priority": rule_data.get("priority", 5),
        "active": True,
        "hitCount": 0,
        "successRate": 0,
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "message": "Regra de classificação criada com sucesso"
    }


@router.get("/stats")
async def get_classification_stats(
    period_days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Estatísticas do sistema de classificação"""

    return {
        "totalItems": 156,
        "classified": 142,
        "needsReview": 14,
        "accuracyScore": 91.8,
        "topCostCenters": [
            {
                "costCenterId": "materia_prima",
                "name": "Matéria-prima",
                "itemCount": 67,
                "totalValue": 125400.50,
                "percentage": 47.1
            },
            {
                "costCenterId": "mao_obra",
                "name": "Mão-de-obra",
                "itemCount": 34,
                "totalValue": 89200.00,
                "percentage": 25.8
            },
            {
                "costCenterId": "equipamentos",
                "name": "Equipamentos",
                "itemCount": 23,
                "totalValue": 45600.30,
                "percentage": 17.2
            },
            {
                "costCenterId": "servicos",
                "name": "Serviços",
                "itemCount": 18,
                "totalValue": 28750.00,
                "percentage": 9.9
            }
        ],
        "recentActivity": [
            {
                "date": "2024-03-16",
                "itemsClassified": 12,
                "accuracyScore": 94.2
            },
            {
                "date": "2024-03-15",
                "itemsClassified": 8,
                "accuracyScore": 89.5
            },
            {
                "date": "2024-03-14",
                "itemsClassified": 15,
                "accuracyScore": 92.1
            }
        ],
        "rulePerformance": [
            {
                "ruleId": "rule_001",
                "ruleName": "Materiais Cimentícios",
                "hitCount": 45,
                "successRate": 95.5
            },
            {
                "ruleId": "rule_002",
                "ruleName": "Serviços de Mão de Obra",
                "hitCount": 23,
                "successRate": 87.2
            }
        ]
    }


@router.post("/classify")
async def classify_items(
    items: List[dict],
    auto_apply: bool = Query(False),
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Classificar itens automaticamente"""

    results = []
    for item in items:
        # Mock classification logic
        description = item.get("description", "").lower()

        if any(keyword in description for keyword in ["cimento", "concreto", "argamassa"]):
            suggested_center = "materia_prima"
            confidence = 95.5
        elif any(keyword in description for keyword in ["mão", "obra", "serviço"]):
            suggested_center = "mao_obra"
            confidence = 87.2
        elif any(keyword in description for keyword in ["equipamento", "aluguel", "máquina"]):
            suggested_center = "equipamentos"
            confidence = 82.3
        else:
            suggested_center = "servicos"
            confidence = 65.0

        results.append({
            "itemId": item.get("id"),
            "itemDescription": item.get("description"),
            "suggestedCostCenter": suggested_center,
            "confidence": confidence,
            "autoClassified": auto_apply and confidence > 85,
            "timestamp": datetime.now().isoformat(),
            "suggestions": [
                {
                    "costCenterId": suggested_center,
                    "costCenterName": "Centro Sugerido",
                    "confidence": confidence,
                    "reasons": [
                        {
                            "description": "Palavra-chave encontrada na descrição",
                            "keyword": "cimento" if suggested_center == "materia_prima" else "serviço"
                        }
                    ]
                }
            ]
        })

    return {
        "results": results,
        "total_classified": len([r for r in results if r["autoClassified"]]),
        "total_items": len(items),
        "success": True
    }


@router.patch("/items/{item_id}/classify")
async def classify_single_item(
    item_id: int,
    cost_center_id: str,
    confidence: float = 100.0,
    current_user: User = Depends(get_suprimentos_user),
    db: Session = Depends(get_db)
):
    """Classificar um item específico manualmente"""

    return {
        "itemId": item_id,
        "costCenterId": cost_center_id,
        "confidence": confidence,
        "classifiedBy": current_user.full_name,
        "classifiedAt": datetime.now().isoformat(),
        "source": "manual",
        "message": "Item classificado com sucesso"
    }