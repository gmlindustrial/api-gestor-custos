# Use uma imagem oficial Python
FROM python:3.11-slim

# Defina o diretório de trabalho
WORKDIR /app

# Instale dependências do sistema necessárias para bcrypt e outras libs
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copie requirements
COPY requirements.txt .

# Instale dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie todo o código da aplicação
COPY . .

# Exponha a porta da aplicação
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "app.main:app"]
