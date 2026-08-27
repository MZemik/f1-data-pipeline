import logging
import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from db_utils import get_engine, ensure_schema_exists

from client import JolpicaClient, JolpicaError
from config import (
    BRONZE_SCHEMA,
    CONSTRUCTOR_STANDINGS_TABLE,
    CURRENT_SEASON,
    DRIVER_STANDINGS_TABLE,
    LOOKBACK_ROUNDS,
    RACE_RESULTS_TABLE,
    RACES_TABLE,
    SPRINT_RESULTS_TABLE,
)

logger = logging.getLogger(__name__)

# bronze table name -> client method name
ENDPOINTS = {
    RACE_RESULTS_TABLE: "get_race_results",
    SPRINT_RESULTS_TABLE: "get_sprint_results",
    DRIVER_STANDINGS_TABLE: "get_driver_standings",
    CONSTRUCTOR_STANDINGS_TABLE: "get_constructor_standings",
}


def get_last_completed_round(client: JolpicaClient, season: int) -> int:
    """How many rounds have actually happened, based on race dates vs today."""
    races = client.get_races(season)
    race_list = races["MRData"]["RaceTable"]["Races"]
    today = datetime.now(timezone.utc).date()
    
    completed = [
        int(race["round"]) for race in race_list
        if datetime.strptime(race["date"], "%Y-%m-%d").date() <= today
    ]
    return max(completed) if completed else 0


def get_rounds_to_process(last_loaded: int, last_available: int, lookback: int = LOOKBACK_ROUNDS) -> list[int]:
    start = max(1, last_loaded - lookback)
    end = last_available
    return list(range(start, end + 1))


def extract_season(client: JolpicaClient, season: int) -> dict[str, list[dict]]:
    """Pull one season's raw payloads into per-table row lists (not yet written to DB).

    Each row is one API call's response, kept as a JSON string, plus the
    metadata needed to identify it. Accumulated in memory and returned so the
    caller can write each table in a single `to_sql(if_exists="replace")` at
    the end of the run — if extraction fails partway through, nothing has
    been written yet and the previous run's bronze data is left intact.
    """
    tables: dict[str, list[dict]] = {RACES_TABLE: []}
    for endpoint in ENDPOINTS:
        tables[endpoint] = []

    try:
        races = client.get_races(season)
    except JolpicaError as error:
        logger.error("Season %s: failed to fetch race calendar: %s", season, error)
        raise 

    race_list = races["MRData"]["RaceTable"]["Races"]
    for race in race_list:     
        tables[RACES_TABLE].append(
            {
                "season": season,
                "round": int(race["round"]),
                "payload": race,
            }
        )

    for race in race_list:
        round_ = int(race["round"])

        for endpoint, method_name in ENDPOINTS.items():
            try:
                fetch = getattr(client, method_name)
                payload = fetch(season, round_)
            except JolpicaError as error:
                logger.error(
                    "Season %s round %s endpoint %s failed: %s",
                    season,
                    round_,
                    endpoint,
                    error,
                )
                continue

            tables[endpoint].append(
                {
                    "season": season,
                    "round": round_,
                    "payload": payload,
                }
            )

    return tables


def load_tables(engine: Engine, tables: dict[str, list[dict]]) -> None:
    for table_name, rows in tables.items():
        df = pd.DataFrame(rows)
        df["_loaded_at"] = datetime.now(timezone.utc)
        df.to_sql(
            table_name,
            engine,
            schema=BRONZE_SCHEMA,
            if_exists="replace",
            index=False,
            dtype={
                "season": Integer,
                "round": Integer,
                "payload": JSONB,
                "_loaded_at": TIMESTAMP(timezone=True),
            },
        )
        logger.info("Loaded %s rows into %s.%s", len(df), BRONZE_SCHEMA, table_name)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    engine = get_engine()
    ensure_schema_exists(engine, BRONZE_SCHEMA)

    with JolpicaClient() as client:
        if not client.test_connection():
            logger.error("Jolpica API unreachable, aborting")
            return

        tables = extract_season(client, CURRENT_SEASON)

    load_tables(engine, tables)


if __name__ == "__main__":
    main()