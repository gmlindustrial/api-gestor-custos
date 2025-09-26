#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import bcrypt

# Load environment
from app.core.config import settings

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    role = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_database_tables():
    """Create all tables and insert initial data"""
    try:
        engine = create_engine(settings.database_url)

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")

        # Create session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # Check if users already exist
        existing_user = db.query(User).filter(User.username == "admin").first()

        if not existing_user:
            # Create default users
            users_data = [
                {
                    "username": "admin",
                    "email": "admin@gmx.com",
                    "full_name": "Administrador",
                    "role": "admin",
                    "password": "admin123"
                },
                {
                    "username": "comercial",
                    "email": "comercial@gmx.com",
                    "full_name": "Usuário Comercial",
                    "role": "comercial",
                    "password": "comercial123"
                },
                {
                    "username": "suprimentos",
                    "email": "suprimentos@gmx.com",
                    "full_name": "Usuário Suprimentos",
                    "role": "suprimentos",
                    "password": "suprimentos123"
                },
                {
                    "username": "diretoria",
                    "email": "diretoria@gmx.com",
                    "full_name": "Diretoria",
                    "role": "diretoria",
                    "password": "diretoria123"
                },
                {
                    "username": "cliente",
                    "email": "cliente@gmx.com",
                    "full_name": "Cliente",
                    "role": "cliente",
                    "password": "cliente123"
                }
            ]

            for user_data in users_data:
                # Hash password
                password = user_data.pop("password")
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    hashed_password=hashed.decode('utf-8'),
                    is_active=True
                )
                db.add(user)

            db.commit()
            print("Default users created!")
        else:
            print("Users already exist, skipping creation")

        db.close()
        print("Database setup completed!")

    except Exception as e:
        print(f"Error setting up database: {e}")

if __name__ == "__main__":
    create_database_tables()