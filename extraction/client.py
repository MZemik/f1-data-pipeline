import logging
import time

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import (
    API_MAX_RETRIES,
    API_RETRY_MAX_WAIT,
    API_RETRY_MIN_WAIT,
    API_RETRY_MULTIPLIER,
    BASE_URL,
    PIPELINE_VERSION,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    TEST_CONNECTION_DELAY_SECONDS,
    TEST_CONNECTION_RETRIES,
)


logger = logging.getLogger(__name__)


class JolpicaError(Exception):
    """Base error raised by the Jolpica client."""


class JolpicaRetryableError(JolpicaError):
    """A transient error for which retrying the request may succeed."""


class JolpicaNonRetryableError(JolpicaError):
    """An error for which retrying the identical request is not useful."""


class JolpicaClient:
    """Client for the Jolpica F1 API."""

    def __init__(self) -> None:
        self.base_url = BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.min_delay = REQUEST_DELAY_SECONDS
        self._last_request_time = 0.0
        self.session.headers.update(
            {
                "User-Agent": f"F1-Data-Pipeline/{PIPELINE_VERSION}",
                "Accept": "application/json",
            }
        )

    def _throttle(self) -> None:
        """Keep a minimum interval between the starts of requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request_time = time.monotonic()

    @retry(
        retry=retry_if_exception_type(JolpicaRetryableError),
        wait=wait_exponential(
            multiplier=API_RETRY_MULTIPLIER,
            min=API_RETRY_MIN_WAIT,
            max=API_RETRY_MAX_WAIT,
        ),
        stop=stop_after_attempt(API_MAX_RETRIES),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Fetch an endpoint, retrying only transient failures.

        Jolpica represents "no data yet" (e.g. a future round) as HTTP 200 with
        an empty list in the endpoint's normal shape, not a 404 — so a real 404
        only occurs for a malformed/out-of-range request and is treated like any
        other non-retryable 4xx, along with invalid JSON.  Timeouts, connection
        failures, 408, 429, and 5xx are retryable.
        """
        self._throttle()
        url = f"{self.base_url}/{endpoint.lstrip('/')}.json"

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except (requests.Timeout, requests.ConnectionError) as error:
            raise JolpicaRetryableError(f"{error} (endpoint: {endpoint})") from error
        
        except requests.RequestException as error:
            raise JolpicaNonRetryableError(f"{error} (endpoint: {endpoint})") from error

        if response.status_code in (408, 429) or 500 <= response.status_code < 600:
            raise JolpicaRetryableError(f"HTTP {response.status_code} for {url}")

        if 400 <= response.status_code < 500:
            raise JolpicaNonRetryableError(f"HTTP {response.status_code} for {url}")

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as error:
             raise JolpicaNonRetryableError(f"Invalid JSON response from {url}") from error

    def test_connection(
        self,
        retries: int = TEST_CONNECTION_RETRIES,
        delay: float = TEST_CONNECTION_DELAY_SECONDS,
    ) -> bool:
        """Perform a lightweight preflight check before starting an extraction.

        The check uses ``HEAD`` against the API root.  It prevents a full run
        from starting when the API is unreachable, rate-limited, unavailable, or
        the configured base URL is invalid.  It intentionally returns a boolean:
        the orchestration layer can then record the run as failed or skipped
        without beginning any endpoint extraction.
        """
        url = f"{self.base_url}.json"
        last_error = "unknown error"

        for attempt in range(1, retries + 1):
            self._throttle()

            try:
                response = self.session.head(url, timeout=REQUEST_TIMEOUT_SECONDS)
            except (requests.Timeout, requests.ConnectionError) as error:
                last_error = str(error)
            except requests.RequestException as error:
                logger.warning("API preflight failed for %s: %s", url, error)
                return False
            else:
                if 200 <= response.status_code < 400:
                    return True

                last_error = f"HTTP {response.status_code}"

                # A client-side response means a bad URL or request. Repeating
                # it cannot make the preflight pass, except for transient 408/429.
                if 400 <= response.status_code < 500 and response.status_code not in (408, 429):
                    logger.warning("API preflight failed for %s: %s", url, last_error)
                    return False

            if attempt < retries:
                time.sleep(delay)

        logger.warning(
            "API preflight failed after %s attempts for %s: %s",
            retries,
            url,
            last_error,
        )
        return False

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"JolpicaClient(base_url='{self.base_url}')"

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