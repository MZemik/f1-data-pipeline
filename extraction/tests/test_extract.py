import pytest
from unittest.mock import Mock
from sqlalchemy import text
from client import JolpicaClient
from extract import get_rounds_to_process, get_last_completed_round, load_tables
from db_utils import get_engine, ensure_schema_exists, ensure_table_exists
from config import TEST_SCHEMA,TEST_TABLE


# Tests for get_rounds_to_process()

def test_get_rounds_to_process_typical_case():
    """Normal case - watermark 12, new data up to 13, lookback 2"""
    assert get_rounds_to_process(12, 13, 2) == [11, 12, 13]

def test_get_rounds_to_process_first_run():
    """Watermark 0 (first run, nothing loaded yet)"""
    assert get_rounds_to_process(0, 5, 2) == [1, 2, 3, 4, 5]

def test_get_rounds_to_process_lookback_would_go_below_1():
    """Lookback would go below round 1 - must clamp to 1, not go negative"""
    assert get_rounds_to_process(1, 2, 5) == [1, 2]  # not [-4, -3, ..., 2]

def test_get_rounds_to_process_nothing_new():
    """last_loaded == last_available - no new rounds, just re-check the lookback window"""
    assert get_rounds_to_process(10, 10, 2) == [9, 10]

def test_get_rounds_to_process_zero_lookback():
    """Lookback 0 - only strictly new rounds, no re-checking"""
    assert get_rounds_to_process(10, 12, 0) == [11, 12]


# Tests for get_last_completed_round()

@pytest.fixture
def mock_client():
    return Mock(spec=JolpicaClient)

def test_get_last_completed_round_typical_case(mock_client):
    mock_client.get_races.return_value = {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {"round": "1", "date": "2020-01-01"},
                    {"round": "2", "date": "2020-01-08"},
                    {"round": "3", "date": "2099-01-01"}
                ]
            }
        }
    }
    
    result = get_last_completed_round(mock_client, 2026)
    assert result == 2


def test_get_last_completed_round_all_rounds_in_future(mock_client):
    mock_client.get_races.return_value = {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {"round": "1", "date": "2098-01-01"},
                    {"round": "2", "date": "2098-01-08"},
                    {"round": "3", "date": "2099-01-01"}
                ]
            }
        }
    }
    
    result = get_last_completed_round(mock_client, 2026)
    assert result == 0


def test_get_last_completed_round_empty_races(mock_client):
    mock_client.get_races.return_value = {
        "MRData": {
            "RaceTable": {
                "Races": [
                ]
            }
        }
    }
    
    result = get_last_completed_round(mock_client, 2026)
    assert result == 0


# Tests for load_tables()

@pytest.fixture
def test_engine():
    engine = get_engine()
    ensure_schema_exists(engine, TEST_SCHEMA)
    ensure_table_exists(engine, TEST_SCHEMA, TEST_TABLE)
    yield engine
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))


def test_load_tables_inserts_new_row(test_engine):
    tables = {TEST_TABLE: [{"season": 2026, "round": 1, "payload": {"data": "x"}}]}
    load_tables(test_engine, TEST_SCHEMA, tables)
    with test_engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT season, round, payload FROM {TEST_SCHEMA}.{TEST_TABLE} WHERE round = :round"),
            {"round": 1}
        ).fetchone()
    assert result is not None
    assert result.season == 2026
    assert result.round == 1
    assert result.payload == {"data": "x"}


def test_load_tables_updates_existing_row(test_engine):
    load_tables(test_engine, TEST_SCHEMA, {TEST_TABLE: [{"season": 2026, "round": 1, "payload": {"data": "x"}}]})
    load_tables(test_engine, TEST_SCHEMA, {TEST_TABLE: [{"season": 2026, "round": 1, "payload": {"data": "y"}}]})
    with test_engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT season, round, payload FROM {TEST_SCHEMA}.{TEST_TABLE} WHERE round = :round"),
            {"round": 1}
        ).fetchone()
    assert result is not None
    assert result.season == 2026
    assert result.round == 1
    assert result.payload == {"data": "y"}


def test_load_tables_skips_write_when_payload_unchanged(test_engine):
    row = {"season": 2026, "round": 1, "payload": {"data": "x"}}
    
    load_tables(test_engine, TEST_SCHEMA, {TEST_TABLE: [row]})
    with test_engine.connect() as conn:
        first_loaded_at = conn.execute(
            text(f"SELECT _loaded_at FROM {TEST_SCHEMA}.{TEST_TABLE} WHERE round = :round"),
            {"round": 1}
        ).scalar()
    
    load_tables(test_engine, TEST_SCHEMA, {TEST_TABLE: [row]})
    with test_engine.connect() as conn:
        second_loaded_at = conn.execute(
            text(f"SELECT _loaded_at FROM {TEST_SCHEMA}.{TEST_TABLE} WHERE round = :round"),
            {"round": 1}
        ).scalar()
    
    assert first_loaded_at == second_loaded_at