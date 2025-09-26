import os
import sys
from sqlalchemy import create_engine, text

# Force UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PGCLIENTENCODING'] = 'utf8'

def test_postgres():
    try:
        # Test with correct password
        url = 'postgresql://postgres:Digitalsegurogml2024!@localhost:5432/postgres'
        engine = create_engine(url)

        with engine.connect() as conn:
            result = conn.execute(text('SELECT 1'))
            print('SUCCESS: Connected with password "admin"')

            # Check if gestor_tarefas database exists
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'gestor_tarefas'"))
            if result.fetchone():
                print('Database gestor_tarefas EXISTS')
            else:
                print('Database gestor_tarefas does NOT exist')
                # Create database
                conn.execute(text('COMMIT'))
                conn.execute(text('CREATE DATABASE gestor_tarefas'))
                print('Created database gestor_tarefas')

    except Exception as e:
        error_str = str(e)
        if 'password authentication failed' in error_str:
            print('FAILED: Password "admin" is incorrect')
        elif 'does not exist' in error_str:
            print('FAILED: User postgres does not exist')
        else:
            print(f'ERROR: {error_str}')

if __name__ == '__main__':
    test_postgres()