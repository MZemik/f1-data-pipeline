import time
import requests
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
from config import (
    BASE_URL, REQUEST_DELAY_SECONDS, PIPELINE_VERSION, CURRENT_SEASON,
    REQUEST_TIMEOUT_SECONDS, API_MAX_RETRIES, API_RETRY_MULTIPLIER,
    API_RETRY_MIN_WAIT, API_RETRY_MAX_WAIT,
)
 
 
class JolpicaAPIError(Exception):
    """Raised for API errors that should NOT be retried (e.g. 4xx client errors)."""
    pass
 
 
class JolpicaClient:
    """Client for Jolpica F1 API"""
 
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.min_delay = REQUEST_DELAY_SECONDS
        self._last_request_time = 0
        self.session.headers.update({
            "User-Agent": f"F1-Data-Pipeline/{PIPELINE_VERSION}",
            "Accept": "application/json"
        })
 
    def _throttle(self):
        """Ensure a minimum gap between requests (burst-limit protection)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request_time = time.time()
 
    @retry(
        wait=wait_exponential(multiplier=API_RETRY_MULTIPLIER, min=API_RETRY_MIN_WAIT, max=API_RETRY_MAX_WAIT),
        stop=stop_after_attempt(API_MAX_RETRIES),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
    )
    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Internal method for a GET request with throttling and retry.
 
        - 404 -> returns an empty-but-valid MRData shape (nothing to retry, this
          round/season simply has no data yet, e.g. a race that hasn't happened).
        - 4xx (other than 404) -> raises JolpicaAPIError immediately, no retry
          (a bad request won't succeed by trying again).
        - 5xx / timeouts / connection errors -> raises requests.exceptions.*,
          which tenacity's retry filter catches and retries with backoff.
        """
        self._throttle()
        url = f"{self.base_url}/{endpoint}.json"
        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
 
        if response.status_code == 404:
            return {"MRData": {"total": "0", "RaceTable": {"Races": []}}}
 
        if 400 <= response.status_code < 500:
            raise JolpicaAPIError(f"Client error {response.status_code} for {url}")
 
        response.raise_for_status()  # 5xx -> raises HTTPError, caught by tenacity's retry
        return response.json()
 
    def test_connection(self) -> bool:
        """Quick check that the API is reachable before running a full extraction."""
        try:
            result = self.get_races(CURRENT_SEASON)
            return "MRData" in result
        except (requests.exceptions.RequestException, JolpicaAPIError):
            return False
 
    def close(self):
        """Close the underlying session."""
        self.session.close()
 
    def __enter__(self):
        return self
 
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
 
    def __repr__(self):
        return f"JolpicaClient(base_url='{self.base_url}')"
 
    # --- Public methods for specific endpoints ---
 
    def get_races(self, season: int) -> dict:
        return self._get(f"{season}/races")
 
    def get_race_results(self, season: int, round: int) -> dict:
        return self._get(f"{season}/{round}/results")
 
    def get_sprint_results(self, season: int, round: int) -> dict:
        return self._get(f"{season}/{round}/sprint")
 
    def get_driver_standings(self, season: int, round: int | None = None) -> dict:
        endpoint = f"{season}/{round}/driverstandings" if round else f"{season}/driverstandings"
        return self._get(endpoint)
 
    def get_constructor_standings(self, season: int, round: int | None = None) -> dict:
        endpoint = f"{season}/{round}/constructorstandings" if round else f"{season}/constructorstandings"
        return self._get(endpoint)
 