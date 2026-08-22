import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# API configuration
BASE_URL = "https://api.jolpi.ca/ergast/f1"
REQUEST_DELAY_SECONDS = 0.5    # 1 / (max requests per second)
REQUEST_TIMEOUT_SECONDS = 10
API_MAX_RETRIES = 5
API_RETRY_MULTIPLIER = 1  
API_RETRY_MIN_WAIT = 2
API_RETRY_MAX_WAIT = 30
PAGE_LIMIT = 100
TEST_CONNECTION_RETRIES = 3
TEST_CONNECTION_DELAY_SECONDS = 2.0

# Seasons
CURRENT_SEASON = datetime.now().year
SEASONS = []

# Schemas
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"
DEV_SCHEMA = "dev"

# Bronze table names
RACES_TABLE = "races"
RACE_RESULTS_TABLE = "race_results"
SPRINT_RESULTS_TABLE = "sprint_results"
DRIVER_STANDINGS_TABLE = "driver_standings"
CONSTRUCTOR_STANDINGS_TABLE = "constructor_standings"

# Pipeline metadata
PIPELINE_VERSION = "1.0.0"