from extract import get_rounds_to_process


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