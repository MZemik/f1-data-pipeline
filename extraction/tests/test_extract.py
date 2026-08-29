from extract import get_rounds_to_process


def test_get_rounds_to_process():
    assert get_rounds_to_process(12, 13, 2) == [11, 12, 13]