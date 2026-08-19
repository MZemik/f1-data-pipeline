import os
from dotenv import load_dotenv

load_dotenv()

SEASON = int(os.environ["JOLPICA_SEASON"])

BASE_URL = os.environ["JOLPICA_BASE_URL"]

RACES_ENDPOINT = "{season}/races.json"
RESULTS_ENDPOINT = "{season}/results.json"
DRIVER_STANDINGS_ENDPOINT = "{season}/driverstandings.json"
CONSTRUCTOR_STANDINGS_ENDPOINT = "{season}/constructorstandings.json"

# 1 / (max requests per second)
REQUEST_DELAY_SECONDS = 0.25

PAGE_LIMIT = 100