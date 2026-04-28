"""
Универсальный адаптер базы данных
Автоматически выбирает PostgreSQL или SQLite
"""
from config import USE_POSTGRES

if USE_POSTGRES:
    from db_postgres import pg_db as db
    print("✅ Using PostgreSQL database")
else:
    from database import db
    print("✅ Using SQLite database")

__all__ = ['db']
