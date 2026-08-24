import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import BRONZE_SCHEMA

def get_engine() -> Engine:
    database_url = os.environ["DATABASE_URL"]
    return create_engine(database_url)


def ensure_schema_exists(engine: Engine, schema: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))


def ensure_bronze_table_exists(engine: Engine, table_name: str) -> None:
    ensure_schema_exists(engine, {BRONZE_SCHEMA})
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {BRONZE_SCHEMA}.{table_name} (
                season INTEGER NOT NULL,
                round INTEGER NOT NULL,
                payload JSONB NOT NULL,
                _loaded_at TIMESTAMPTZ NOT NULL,
                UNIQUE (season, round);        
            )
        """))