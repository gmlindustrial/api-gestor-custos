#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_database():
    try:
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            # Check tables
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """))

            tables = [row[0] for row in result.fetchall()]
            print("Tables in database:", tables)

            # Check users table structure if exists
            if 'users' in tables:
                result = conn.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                    AND table_schema = 'public'
                """))

                columns = [(row[0], row[1]) for row in result.fetchall()]
                print("Users table columns:", columns)

                # Check existing users
                result = conn.execute(text("SELECT id, username, role FROM users LIMIT 5"))
                users = [dict(row._mapping) for row in result.fetchall()]
                print("Existing users:", users)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database()