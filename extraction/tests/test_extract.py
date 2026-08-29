import pytest
from unittest.mock import Mock
from client import JolpicaClient
from extract import get_rounds_to_process, get_last_completed_round


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