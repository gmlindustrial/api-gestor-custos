#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para testar endpoint de contratos"""

import traceback
from app.core.database import get_db
from app.models.contracts import Contract
from app.models.users import User
from app.schemas.contracts import ContractResponse, ContractListResponse

def test_contracts_endpoint():
    """Testar endpoint de contratos"""
    try:
        print("Testando query de contratos...")

        # Simular o que o endpoint faz
        db = next(get_db())

        # Query base
        query = db.query(Contract)
        total = query.count()
        contracts = query.all()

        print(f"Total de contratos: {total}")
        print(f"Contratos encontrados: {len(contracts)}")

        # Tentar converter para response schema
        contract_responses = []
        for contract in contracts:
            print(f"Processando contrato: {contract.nome_projeto}")

            # Calcular valores derivados
            valor_realizado = float(contract.valor_original) * 0.6
            saldo_contrato = float(contract.valor_original) - valor_realizado
            percentual_realizado = (valor_realizado / float(contract.valor_original)) * 100
            economia_obtida = float(contract.valor_original) * (float(contract.meta_reducao_percentual) / 100)

            contract_data = {
                "id": contract.id,
                "numero_contrato": contract.numero_contrato,
                "nome_projeto": contract.nome_projeto,
                "cliente": contract.cliente,
                "tipo_contrato": contract.tipo_contrato,
                "valor_original": contract.valor_original,
                "meta_reducao_percentual": contract.meta_reducao_percentual,
                "status": contract.status,
                "data_inicio": contract.data_inicio,
                "data_fim_prevista": contract.data_fim_prevista,
                "data_fim_real": contract.data_fim_real,
                "observacoes": contract.observacoes,
                "criado_por": contract.criado_por,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "valor_realizado": valor_realizado,
                "saldo_contrato": saldo_contrato,
                "percentual_realizado": percentual_realizado,
                "economia_obtida": economia_obtida,
                "percentual_economia": (economia_obtida / float(contract.valor_original)) * 100 if contract.valor_original > 0 else 0
            }

            print(f"Dados do contrato preparados: {contract_data['numero_contrato']}")

            # Tentar criar response schema
            contract_response = ContractResponse(**contract_data)
            contract_responses.append(contract_response)
            print(f"Response schema criado com sucesso")

        # Tentar criar response final
        final_response = ContractListResponse(
            contracts=contract_responses,
            total=total,
            page=1,
            per_page=10
        )

        print("SUCCESS: Endpoint funcionaria corretamente!")
        print(f"Resposta final: {len(final_response.contracts)} contratos")

    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_contracts_endpoint()