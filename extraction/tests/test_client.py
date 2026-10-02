import pytest
import responses
import requests
from client import JolpicaClient, JolpicaRetryableError, JolpicaNonRetryableError
from config import API_MAX_RETRIES

URL = "https://api.jolpi.ca/ergast/f1/2026/races.json"
OK = {"MRData": {"RaceTable": {"Races": []}}}

HEAD_URL = "https://api.jolpi.ca/ergast/f1.json"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Skip real waiting (tenacity backoff + throttle) so tests run instantly."""
    monkeypatch.setattr("time.sleep", lambda seconds: None)


# Tests for _get()

@responses.activate
def test_get_returns_data_on_200():
    responses.add(responses.GET, URL, json=OK, status=200)
    
    client = JolpicaClient()
    result = client.get_races(2026)
    
    assert result == {"MRData": {"RaceTable": {"Races": []}}}
    assert len(responses.calls) == 1


@responses.activate
def test_get_raises_nonretryable_on_4xx_using_404_example():
    responses.add(responses.GET, URL, status=404)
    
    client = JolpicaClient()
    
    with pytest.raises(JolpicaNonRetryableError):
        client.get_races(2026)

    assert len(responses.calls) == 1


@responses.activate
def test_get_retries_on_408_then_succeeds():
    responses.add(responses.GET, URL, status=408)
    responses.add(responses.GET, URL, json=OK, status=200)

    result = JolpicaClient().get_races(2026)

    assert result == OK
    assert len(responses.calls) == 2


@responses.activate
def test_get_retries_on_429_then_succeeds():
    responses.add(responses.GET, URL, status=429)
    responses.add(responses.GET, URL, json=OK, status=200)

    result = JolpicaClient().get_races(2026)

    assert result == OK
    assert len(responses.calls) == 2


@responses.activate
def test_get_retries_on_5xx_then_succeeds():
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, json=OK, status=200)

    result = JolpicaClient().get_races(2026)

    assert result == OK
    assert len(responses.calls) == 2


@responses.activate
def test_get_raises_retryable_after_all_retries_exhausted():
    responses.add(responses.GET, URL, status=503)

    with pytest.raises(JolpicaRetryableError):
        JolpicaClient().get_races(2026)

    assert len(responses.calls) == API_MAX_RETRIES


@responses.activate
def test_get_raises_nonretryable_on_invalid_json():
    responses.add(responses.GET, URL, body="not json", status=200)

    with pytest.raises(JolpicaNonRetryableError):
        JolpicaClient().get_races(2026)

    assert len(responses.calls) == 1


@responses.activate
def test_get_retries_on_connection_error_then_succeeds():
    responses.add(responses.GET, URL, body=requests.ConnectionError("boom"))
    responses.add(responses.GET, URL, json=OK, status=200)

    result = JolpicaClient().get_races(2026)

    assert result == OK
    assert len(responses.calls) == 2


@responses.activate
def test_get_retries_on_timeout_then_succeeds():
    responses.add(responses.GET, URL, body=requests.Timeout("too slow"))
    responses.add(responses.GET, URL, json=OK, status=200)

    result = JolpicaClient().get_races(2026)

    assert result == OK
    assert len(responses.calls) == 2


@responses.activate
def test_get_raises_nonretryable_on_other_request_exception():
    responses.add(responses.GET, URL, body=requests.RequestException("weird"))

    with pytest.raises(JolpicaNonRetryableError):
        JolpicaClient().get_races(2026)

    assert len(responses.calls) == 1


# Tests for test_connection()

@responses.activate
def test_connection_returns_true_on_200():
    responses.add(responses.HEAD, HEAD_URL, status=200)

    assert JolpicaClient().test_connection(retries=3) is True
    assert len(responses.calls) == 1


@responses.activate
@pytest.mark.parametrize("status", [408, 429, 503])
def test_connection_retries_on_transient_status_then_succeeds(status):
    responses.add(responses.HEAD, HEAD_URL, status=status)
    responses.add(responses.HEAD, HEAD_URL, status=200)

    assert JolpicaClient().test_connection(retries=3) is True
    assert len(responses.calls) == 2


@responses.activate
@pytest.mark.parametrize("status", [400, 404])
def test_connection_returns_false_immediately_on_client_error(status):
    responses.add(responses.HEAD, HEAD_URL, status=status)

    assert JolpicaClient().test_connection(retries=3) is False
    assert len(responses.calls) == 1


@responses.activate
def test_connection_returns_false_after_all_retries_on_503():
    responses.add(responses.HEAD, HEAD_URL, status=503)

    assert JolpicaClient().test_connection(retries=3) is False
    assert len(responses.calls) == 3


@responses.activate
def test_connection_retries_on_connection_error_then_succeeds():
    responses.add(responses.HEAD, HEAD_URL, body=requests.ConnectionError("boom"))
    responses.add(responses.HEAD, HEAD_URL, status=200)

    assert JolpicaClient().test_connection(retries=3) is True
    assert len(responses.calls) == 2


@responses.activate
def test_connection_retries_on_timeout_then_succeeds():
    responses.add(responses.HEAD, HEAD_URL, body=requests.Timeout("too slow"))
    responses.add(responses.HEAD, HEAD_URL, status=200)

    assert JolpicaClient().test_connection(retries=3) is True
    assert len(responses.calls) == 2


@responses.activate
def test_connection_returns_false_after_all_retries_on_connection_error():
    responses.add(responses.HEAD, HEAD_URL, body=requests.ConnectionError("boom"))

    assert JolpicaClient().test_connection(retries=3) is False
    assert len(responses.calls) == 3


@responses.activate
def test_connection_returns_false_immediately_on_other_request_exception():
    responses.add(responses.HEAD, HEAD_URL, body=requests.RequestException("weird"))

    assert JolpicaClient().test_connection(retries=3) is False
    assert len(responses.calls) == 1