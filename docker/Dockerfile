FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicação
COPY . .

# Criar diretórios
RUN mkdir -p logs uploads ml_models

# Variáveis de ambiente
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expor porta
EXPOSE 8000

# Comando de execução
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
