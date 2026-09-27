import pytest
from db_utils import get_engine, ensure_schema_exists, ensure_table_exists, get_last_loaded_round
from config import TEST_SCHEMA, TEST_TABLE
from extract import load_tables
from sqlalchemy import text

@pytest.fixture
def test_engine():
    engine = get_engine()
    ensure_schema_exists(engine, TEST_SCHEMA)
    ensure_table_exists(engine, TEST_SCHEMA, TEST_TABLE)
    yield engine
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))


# Tests for get_last_loaded_round()

def test_get_last_loaded_round_empty_table(test_engine):
    assert get_last_loaded_round(test_engine, TEST_SCHEMA, TEST_TABLE) == 0


def test_get_last_loaded_round_with_data(test_engine):
    load_tables(test_engine, TEST_SCHEMA, {TEST_TABLE: [
        {"season": 2026, "round": 1, "payload": {}},
        {"season": 2026, "round": 5, "payload": {}},
    ]})
    assert get_last_loaded_round(test_engine, TEST_SCHEMA, TEST_TABLE) == 5