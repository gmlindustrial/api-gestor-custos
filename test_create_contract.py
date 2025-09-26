#!/usr/bin/env python3
"""Teste do endpoint de criação de contratos"""

import requests
import json
from datetime import datetime, date

# URL base da API
BASE_URL = "http://localhost:8000/api/v1"

def test_create_contract():
    print("Testando criação de contrato...")

    # Primeiro, fazer login para obter token
    login_data = {
        "username": "admin",  # Assumindo que existe um usuário admin
        "password": "admin"   # Substitua pela senha correta
    }

    # Tentar fazer login
    try:
        login_response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        print(f"Login response status: {login_response.status_code}")

        if login_response.status_code != 200:
            print("Erro no login - vamos testar sem autenticação")
            print(f"Response: {login_response.text}")
            token = None
        else:
            token_data = login_response.json()
            token = token_data.get("access_token")
            print(f"Token obtido: {token[:20]}..." if token else "Token não encontrado")
    except Exception as e:
        print(f"Erro no login: {e}")
        token = None

    # Headers para a requisição
    headers = {
        "Content-Type": "application/json"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Dados do contrato no formato que o backend espera
    contract_data = {
        "numero_contrato": f"CONT-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "nome_projeto": "Contrato de Teste API",
        "cliente": "Cliente Teste LTDA",
        "tipo_contrato": "material_produto",
        "valor_original": 150000.50,
        "meta_reducao_percentual": 5.0,
        "data_inicio": datetime.now().isoformat(),
        "data_fim_prevista": "2024-12-31T23:59:59",
        "observacoes": "Contrato criado via teste da API",
        "budget_items": [
            {
                "codigo_item": "MAT-001",
                "descricao": "Material de construção básico",
                "centro_custo": "Matéria-Prima",
                "unidade": "UN",
                "quantidade_prevista": 100.0,
                "peso_previsto": 50.0,
                "valor_unitario_previsto": 25.50,
                "valor_total_previsto": 2550.00
            },
            {
                "codigo_item": "MAT-002",
                "descricao": "Cimento Portland",
                "centro_custo": "Matéria-Prima",
                "unidade": "SC",
                "quantidade_prevista": 200.0,
                "valor_unitario_previsto": 32.00,
                "valor_total_previsto": 6400.00
            }
        ]
    }

    print(f"Enviando dados: {json.dumps(contract_data, indent=2, ensure_ascii=False)}")

    try:
        # Fazer requisição para criar contrato
        response = requests.post(
            f"{BASE_URL}/contracts",
            headers=headers,
            json=contract_data
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print("✓ Contrato criado com sucesso!")
            print(f"ID do contrato: {result.get('id')}")
            print(f"Número do contrato: {result.get('numero_contrato')}")
            print(f"Nome do projeto: {result.get('nome_projeto')}")
            print(f"Cliente: {result.get('cliente')}")
            print(f"Valor original: R$ {result.get('valor_original')}")
            return True
        else:
            print(f"✗ Erro ao criar contrato")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ Erro: Não foi possível conectar ao servidor")
        print("Verifique se o backend está rodando em http://localhost:8000")
        return False
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
        return False

def test_get_contracts():
    print("\nTestando listagem de contratos...")

    try:
        response = requests.get(f"{BASE_URL}/contracts")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            contracts = result.get('contracts', [])
            print(f"✓ Encontrados {len(contracts)} contratos")

            for contract in contracts[:3]:  # Mostrar apenas os 3 primeiros
                print(f"  - {contract.get('numero_contrato')}: {contract.get('nome_projeto')}")

            return True
        else:
            print(f"✗ Erro ao listar contratos: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Erro ao listar contratos: {e}")
        return False

if __name__ == "__main__":
    print("=== TESTE DOS ENDPOINTS DE CONTRATOS ===\n")

    # Testar listagem primeiro
    list_success = test_get_contracts()

    # Testar criação
    create_success = test_create_contract()

    print(f"\n=== RESULTADO DOS TESTES ===")
    print(f"Listagem de contratos: {'✓ OK' if list_success else '✗ FALHOU'}")
    print(f"Criação de contrato: {'✓ OK' if create_success else '✗ FALHOU'}")

    if create_success:
        # Testar listagem novamente para ver o novo contrato
        print("\nVerificando se o contrato foi criado...")
        test_get_contracts()