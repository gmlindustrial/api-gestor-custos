#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.auth import get_password_hash

def update_user_password():
    try:
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            # Create admin user with known password
            hashed_password = get_password_hash("admin123")

            # Update Bruno Brito's password
            conn.execute(text("""
                UPDATE users
                SET password = :password
                WHERE username = 'Bruno Brito'
            """), {"password": hashed_password})

            conn.commit()
            print("User Bruno Brito updated with password: admin123")

            # Also create a simple admin user if doesn't exist
            result = conn.execute(text("SELECT id FROM users WHERE username = 'admin'"))
            if not result.fetchone():
                hashed_admin = get_password_hash("admin123")
                conn.execute(text("""
                    INSERT INTO users (username, email, password, role, isActive)
                    VALUES (:username, :email, :password, :role, :active)
                """), {
                    "username": "admin",
                    "email": "admin@gmx.com",
                    "password": hashed_admin,
                    "role": "admin",
                    "active": True
                })
                conn.commit()
                print("Created admin user with password: admin123")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_user_password()