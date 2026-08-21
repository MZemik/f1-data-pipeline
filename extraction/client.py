import time
import requests
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
from config import BASE_URL, REQUEST_DELAY_SECONDS, PAGE_LIMIT


class JolpicaClient:
    """Client for Jolpica F1 API"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'F1-Data-Pipeline/1.0',
            'Accept': 'application/json'
        })