#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_users():
    try:
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            # Check users and their passwords
            result = conn.execute(text("SELECT id, username, email, password, role FROM users LIMIT 10"))
            users = [dict(row._mapping) for row in result.fetchall()]

            print("Users in database:")
            for user in users:
                print(f"ID: {user['id']}, Username: {user['username']}, Role: {user['role']}")
                print(f"  Email: {user['email']}")
                print(f"  Password: {user['password'][:50] if user['password'] else 'None'}...")
                print()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()