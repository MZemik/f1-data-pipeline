import json
import logging
from pathlib import Path
from sqlalchemy.engine import Engine
from config import BRONZE_SCHEMA
from extract import load_tables
from db_utils import get_engine, ensure_schema_exists, ensure_table_exists

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SEASON = 2026


def extract_fixtures(directory: Path, engine: Engine, season: int, schema: str) -> dict[str, list[dict]]:
    tables: dict[str, list[dict]] = {}

    for file in directory.glob("*.json"):
        data = json.loads(file.read_text())
        tables[file.stem] = []
        ensure_table_exists(engine, schema, file.stem)
        for round_, payload in data.items():
            tables[file.stem].append(
                {
                    "season": season,
                    "round": int(round_),
                    "payload": payload,
                }
            )

    return tables


def main():
    logging.basicConfig(level=logging.INFO)
    engine = get_engine()
    ensure_schema_exists(engine, BRONZE_SCHEMA)
    tables = extract_fixtures(FIXTURES_DIR, engine, SEASON, BRONZE_SCHEMA)
    load_tables(engine, BRONZE_SCHEMA, tables)


if __name__ == "__main__":
    main()