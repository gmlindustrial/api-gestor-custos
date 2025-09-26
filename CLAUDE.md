# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **GMX - Módulo de Custos de Obras** (Construction Cost Management Module), a new section within the existing **Gestor de Tarefas** (Task Manager ERP) system. It provides comprehensive cost control and management for construction projects with real-time integration to existing GMX systems.

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### PostgreSQL Database Setup
```bash
# Install PostgreSQL (if not already installed)
# Windows: Download from https://www.postgresql.org/download/windows/
# Linux: sudo apt-get install postgresql postgresql-contrib
# macOS: brew install postgresql

# Start PostgreSQL service
# Windows: Services → PostgreSQL
# Linux: sudo systemctl start postgresql
# macOS: brew services start postgresql

# Create database user (if needed)
sudo -u postgres createuser --interactive --pwprompt

# Create the unified database
createdb gestor_tarefas -O your_username

# Or if using default postgres user:
sudo -u postgres createdb gestor_tarefas

# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Test database connection
python test_connection.py

# Manual table creation (fallback)
python create_tables_manual.py
```

### Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with actual PostgreSQL credentials:
# DATABASE_URL=postgresql://username:password@localhost/gestor_tarefas
# SECRET_KEY=your-secure-secret-key-here
# DEBUG=True  # Set to False in production
```

### Quick Start
```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create database
createdb gestor_tarefas

# 4. Run migrations
alembic upgrade head

# 5. Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture Overview

### Tech Stack
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Unified database (shared with Gestor de Tarefas)
- **Alembic**: Database migrations
- **Pydantic**: Data validation and serialization
- **JWT**: Authentication tokens
- **Pandas**: Excel/CSV data processing
- **ReportLab**: PDF report generation
- **Redis**: Caching and sessions (optional)

### User Roles & Permissions
- **Admin**: Full system access
- **Diretoria**: Executive dashboards, strategic KPIs, contract oversight
- **Comercial**: Contract creation, budget imports (QQP Cliente), client management
- **Suprimentos**: Purchase orders, supplier management, quotations, internal reports
- **Cliente**: Synthetic reports, account statements, limited contract view

### Main Use Cases
1. **Budget Import**: Commercial users import cost composition spreadsheets (QQP Cliente tab)
2. **Purchase Management**: Procurement users register purchase orders with 3 quotations minimum
3. **Analytical Reports**: Internal detailed reports with full item breakdown
4. **Synthetic Reports**: Client-facing account statements with essential info only
5. **Contract Balance Tracking**: Real-time contract balance calculation
6. **Management Dashboards**: Role-specific KPI dashboards
7. **AI Assistant Integration**: Specialized cost analysis AI chat interface

### Project Structure
```
app/
├── api/
│   ├── routes/
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── contracts.py      # Contract CRUD & metrics
│   │   ├── purchases.py      # Purchase orders, suppliers, quotations
│   │   ├── reports.py        # Analytical/synthetic report generation
│   │   ├── dashboards.py     # KPI dashboards (Suprimentos/Diretoria)
│   │   └── import_data.py    # Excel/XML data import endpoints
│   └── dependencies.py       # Role-based auth dependencies
├── core/
│   ├── auth.py              # JWT + role-based authentication
│   ├── config.py            # Environment settings
│   └── database.py          # PostgreSQL connection
├── models/                  # SQLAlchemy models
│   ├── contracts.py         # Contracts, budgets, cost centers
│   ├── purchases.py         # Purchase orders, quotations, suppliers
│   ├── users.py            # User management with roles
│   ├── attachments.py      # Document/certificate storage
│   └── audit.py            # Change tracking & audit logs
├── schemas/                # Pydantic DTOs
├── services/               # Business logic
│   ├── import_service.py   # Excel/XML processing
│   ├── report_service.py   # PDF/Excel report generation
│   ├── dashboard_service.py # KPI calculations
│   └── ai_service.py       # AI assistant integration
└── main.py                # Application entry point
```

### Key Domain Concepts

#### Contract Types
- **Material/Produto**: Physical goods with quantity, weight, unit price tracking
- **Serviço**: Services with normal hours, overtime hours, salary tracking

#### Cost Centers
- Matéria-prima (Raw materials)
- Mobilização (Mobilization)
- Mão-de-obra (Labor)
- Equipment/Services (configurable)

#### KPIs & Calculations
- **Contract Balance**: `contract_value - (direct_purchases + gmx_issued_invoices)`
- **Realization %**: `actual_spent / budgeted_amount * 100`
- **Cost Savings**: `budgeted - actual` (in R$ and %)
- **Target Achievement**: Configurable cost reduction goals per contract

### Database Configuration
- **Primary DB**: PostgreSQL (unified with Gestor de Tarefas)
- **Connection**: Via SQLAlchemy with connection pooling
- **Migrations**: Alembic for schema versioning
- **Backup**: Daily automated backups required
- **Audit Trail**: All changes logged with user tracking

### Integration Points
- **Otimizador de Corte**: Material optimization data exchange
- **Gestor de Tarefas**: Task and project data synchronization
- **OneDrive/Google Drive**: Automated invoice/document import
- **AI Assistant**: Internal data analysis and recommendations

### API Structure
- **Base Path**: `/api/v1/`
- **Authentication**: JWT with role-based access control
- **CORS**: Configured for frontend integration
- **Health Check**: `/health`
- **Documentation**: Auto-generated OpenAPI/Swagger

### Development Notes
- Database must be PostgreSQL for production compatibility
- All financial data requires audit trail
- Reports must support PDF and Excel export
- File uploads limited to approved formats (Excel, XML, PDF)
- Real-time dashboard updates (max 60min refresh)
- Mobile-responsive design required