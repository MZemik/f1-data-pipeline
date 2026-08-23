import logging
import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from db_utils import get_engine, ensure_schema_exists

from client import JolpicaClient, JolpicaError
from config import (
    BRONZE_SCHEMA,
    CONSTRUCTOR_STANDINGS_TABLE,
    CURRENT_SEASON,
    DRIVER_STANDINGS_TABLE,
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


def extract_season(
    client: JolpicaClient, season: int, round_limit: int | None = None
) -> dict[str, list[dict]]:
    """Pull one season's raw payloads into per-table row lists (not yet written to DB).

    Each row is one API call's response, kept as a JSON string, plus the
    metadata needed to identify it. Accumulated in memory and returned so the
    caller can write each table in a single `to_sql(if_exists="replace")` at
    the end of the run — if extraction fails partway through, nothing has
    been written yet and the previous run's bronze data is left intact.

    `round_limit` is a dev-only convenience to cut API calls while testing —
    it slices which rounds get results/sprint/standings pulled, not the
    incremental "lookback window" loading planned for Phase 7. `bronze.races`
    still always gets the full calendar (one cheap call).
    """
    tables: dict[str, list[dict]] = {RACES_TABLE: []}
    for endpoint in ENDPOINTS:
        tables[endpoint] = []

    races = client.get_races(season)
    race_list = races["MRData"]["RaceTable"]["Races"]
    for race in race_list:     
        tables[RACES_TABLE].append(
            {
                "season": season,
                "round": int(race["round"]),
                "payload": race,
            }
        )

    if round_limit is not None:
        race_list = race_list[:round_limit]

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
            dtype={"payload": JSONB},
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

        round_limit_raw = os.environ.get("EXTRACT_ROUND_LIMIT")
        round_limit = int(round_limit_raw) if round_limit_raw else None
        tables = extract_season(client, CURRENT_SEASON, round_limit=round_limit)

    load_tables(engine, tables)


if __name__ == "__main__":
    main()
