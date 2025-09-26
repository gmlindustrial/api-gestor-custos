# GMX - Módulo de Custos de Obras - Backend

API backend desenvolvida em FastAPI para o sistema de gestão de custos de construção da GMX.

## Funcionalidades Implementadas

### 🔐 Autenticação e Autorização
- Sistema de login com JWT tokens
- Controle de acesso baseado em perfis:
  - **Comercial**: Gestão de contratos e orçamentos
  - **Suprimentos**: Gestão de compras e fornecedores
  - **Diretoria**: Acesso a dashboards executivos e relatórios estratégicos
  - **Cliente**: Relatórios sintéticos e conta-corrente
  - **Admin**: Acesso completo ao sistema

### 📋 Gestão de Contratos
- CRUD completo de contratos
- Suporte a contratos de material/produto e serviço
- Gestão de orçamentos previstos (QQP Cliente)
- Cálculo automático de métricas:
  - Valor realizado vs previsto
  - Saldo do contrato
  - Percentual de economia
  - Atingimento de metas

### 🛒 Gestão de Compras
- Cadastro e aprovação de fornecedores
- Gestão de ordens de compra com múltiplas cotações
- Sistema de seleção de fornecedores com justificativa
- Controle de notas fiscais e pagamentos
- Rastreabilidade completa do processo

### 📊 Relatórios
- **Relatório Analítico**: Detalhado para uso interno (Suprimentos/Diretoria)
- **Relatório Sintético**: Resumido para clientes
- **Conta-Corrente**: Saldo e movimentações do contrato
- Exportação em PDF, Excel e JSON
- Filtros avançados por período, contrato, fornecedor

### 📈 Dashboards e KPIs
- **Dashboard de Suprimentos**: 
  - Ordens de compra, cotações pendentes
  - Economia obtida, fornecedores aprovados
  - Gráficos de gastos por centro de custo
- **Dashboard Executivo**:
  - KPIs estratégicos, economia total
  - Progresso dos contratos, metas atingidas
  - Identificação de riscos e oportunidades

### 📥 Importação de Dados
- Importação de orçamentos de planilhas Excel (QQP Cliente)
- Importação de notas fiscais de XML (NF-e) e Excel
- Classificação automática por centro de custo
- Importação em lote de múltiplos arquivos
- Validação e tratamento de erros

### 🔍 Auditoria e Controle
- Log completo de todas as operações
- Versionamento de anexos
- Controle de acesso granular
- Histórico de alterações

## Tecnologias Utilizadas

- **FastAPI**: Framework web moderno para APIs
- **SQLAlchemy**: ORM para banco de dados
- **PostgreSQL**: Banco de dados principal
- **Alembic**: Migrações de banco de dados
- **Pydantic**: Validação e serialização de dados
- **JWT**: Autenticação por tokens
- **Pandas**: Processamento de planilhas
- **ReportLab**: Geração de relatórios PDF
- **Redis**: Cache e sessões (opcional)

## Estrutura do Projeto

```
backend/
├── app/
│   ├── api/            # Rotas da API
│   │   ├── routes/     # Endpoints organizados por módulo
│   │   └── dependencies.py  # Dependências de autenticação
│   ├── core/           # Configurações centrais
│   │   ├── auth.py     # Autenticação JWT
│   │   ├── config.py   # Configurações da aplicação
│   │   └── database.py # Conexão com banco de dados
│   ├── models/         # Modelos SQLAlchemy
│   ├── schemas/        # Schemas Pydantic (DTOs)
│   ├── services/       # Lógica de negócio
│   └── main.py         # Aplicação principal
├── alembic/            # Migrações do banco
├── requirements.txt    # Dependências Python
└── README.md          # Esta documentação
```

## Instalação e Configuração

### Pré-requisitos
- Python 3.9+
- PostgreSQL
- Redis (opcional)

### 1. Instalar Dependências
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente
```bash
cp .env.example .env
# Editar .env com suas configurações
```

### 3. Configurar Banco de Dados
```bash
# Criar banco PostgreSQL
createdb gmx_custos

# Executar migrações
alembic upgrade head
```

### 4. Executar Aplicação
```bash
# Desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints da API

### Autenticação
- `POST /api/v1/auth/login` - Login do usuário
- `POST /api/v1/auth/register` - Cadastro de usuário
- `GET /api/v1/auth/me` - Informações do usuário logado

### Contratos
- `GET /api/v1/contracts/` - Listar contratos
- `POST /api/v1/contracts/` - Criar contrato
- `GET /api/v1/contracts/{id}` - Detalhes do contrato
- `PUT /api/v1/contracts/{id}` - Atualizar contrato
- `DELETE /api/v1/contracts/{id}` - Excluir contrato
- `GET /api/v1/contracts/{id}/metrics` - Métricas do contrato

### Compras
- `GET /api/v1/purchases/suppliers/` - Listar fornecedores
- `POST /api/v1/purchases/suppliers/` - Cadastrar fornecedor
- `PATCH /api/v1/purchases/suppliers/{id}/approve` - Aprovar fornecedor
- `GET /api/v1/purchases/orders/` - Listar ordens de compra
- `POST /api/v1/purchases/orders/` - Criar ordem de compra
- `GET /api/v1/purchases/invoices/` - Listar notas fiscais
- `POST /api/v1/purchases/invoices/` - Criar nota fiscal

### Relatórios
- `POST /api/v1/reports/generate` - Gerar relatório
- `GET /api/v1/reports/download/{filename}` - Download de arquivo
- `GET /api/v1/reports/analytical/preview` - Preview relatório analítico
- `GET /api/v1/reports/balance/preview` - Preview conta-corrente

### Dashboards
- `GET /api/v1/dashboards/supplies` - Dashboard de Suprimentos
- `GET /api/v1/dashboards/executive` - Dashboard Executivo
- `GET /api/v1/dashboards/kpis/summary` - Resumo de KPIs

### Importação
- `POST /api/v1/import/validate-file` - Validar arquivo
- `POST /api/v1/import/budget/excel` - Importar orçamento Excel
- `POST /api/v1/import/invoice/xml` - Importar NF XML
- `POST /api/v1/import/invoice/excel` - Importar NF Excel
- `POST /api/v1/import/bulk/invoices` - Importação em lote

## Configuração de Produção

### Variáveis de Ambiente
```bash
DATABASE_URL=postgresql://user:pass@localhost/gmx_custos
SECRET_KEY=your-super-secret-key-here
CORS_ORIGINS=https://yourdomain.com
DEBUG=False
```

### Docker (Opcional)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Integração com Frontend

A API foi projetada para integrar perfeitamente com o frontend React existente. Os endpoints seguem padrões RESTful e retornam dados no formato esperado pelos hooks e serviços do frontend.

### Exemplo de Integração
```typescript
// Frontend (TypeScript/React)
const { data: contracts } = useQuery('contracts', () =>
  api.get('/api/v1/contracts/').then(res => res.data)
);
```

## Monitoramento e Logs

- Todos os endpoints incluem logs detalhados
- Auditoria completa de operações críticas  
- Métricas de performance disponíveis
- Health check endpoint: `GET /health`

## Segurança

- Autenticação JWT com expiração configurável
- Controle de acesso baseado em roles
- Validação rigorosa de entrada de dados
- Sanitização de uploads de arquivos
- Headers de segurança implementados

## Suporte e Manutenção

Para suporte técnico ou dúvidas sobre a implementação, consulte a documentação do código ou entre em contato com a equipe de desenvolvimento.