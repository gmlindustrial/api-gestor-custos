FROM python:3.11-slim

# Evita .pyc e força stdout/stderr direto
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Atualiza pip e instala dependências do sistema
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    pip install --upgrade pip && \
    rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação
COPY . .

# Gunicorn com workers uvicorn
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
