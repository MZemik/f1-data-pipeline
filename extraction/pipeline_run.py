import uuid
from sqlalchemy import text
from sqlalchemy.engine import Engine
from db_utils import ensure_schema_exists
from config import META_SCHEMA


def ensure_pipeline_logs_table_exists(engine: Engine) -> None:
    ensure_schema_exists(engine, META_SCHEMA)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS meta.pipeline_logs (
                ...
            )
        """))


class PipelineRun:
    """Class for managing metadata and pipeline runs"""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.run_id = uuid.uuid4()

    def __enter__(self):
        ensure_pipeline_logs_table_exists(self.engine)
        return self