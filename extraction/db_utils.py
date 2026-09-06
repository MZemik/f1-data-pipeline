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


def ensure_table_exists(engine: Engine, schema: str, table_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.{table_name} (
                season INTEGER NOT NULL,
                round INTEGER NOT NULL,
                payload JSONB NOT NULL,
                _loaded_at TIMESTAMPTZ NOT NULL,
                UNIQUE (season, round)        
            )
        """))


def get_last_loaded_round(engine: Engine, table_name: str) -> int:
    """Watermark: highest round currently present in a Bronze table.
    Returns 0 if the table doesn't exist yet or is empty (first run)."""
    query = text(f"SELECT MAX(round) AS max_round FROM {BRONZE_SCHEMA}.{table_name}")
    with engine.connect() as conn:
        result = conn.execute(query).scalar()
    return result or 0