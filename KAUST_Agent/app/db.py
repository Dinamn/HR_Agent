from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv


load_dotenv()

DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def run_select(sql: str, params: dict = None):
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        cols = result.keys()
        rows = [dict(zip(cols, r)) for r in result.fetchall()]
    return rows

def run_write(sql: str, params: dict = None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

