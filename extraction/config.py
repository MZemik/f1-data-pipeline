import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# API configuration
BASE_URL = "https://api.jolpi.ca/ergast/f1/"
REQUEST_DELAY_SECONDS = 0.25    # 1 / (max requests per second)
REQUEST_TIMEOUT_SECONDS = 10
API_MAX_RETRIES = 5
API_RETRY_MULTIPLIER = 1  
API_RETRY_MIN_WAIT = 2
API_RETRY_MAX_WAIT = 30
PAGE_LIMIT = 100

# Seasons
CURRENT_SEASON = datetime.now().year
SEASONS = []

# Pipeline metadata
PIPELINE_VERSION = "1.0.0"