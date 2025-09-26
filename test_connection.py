import psycopg2
import os
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

try:
    # Tentar conectar usando as configurações do .env
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_DATABASE", "db"),
        user=os.getenv("DB_USERNAME", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )
    print("Conexao com PostgreSQL bem-sucedida!")
    conn.close()
except Exception as e:
    print(f"Erro na conexao: {e}")