# F1 Data Pipeline

An end-to-end ELT pipeline for the 2026 Formula 1 season. It pulls race data from the [Jolpica-F1 API](https://github.com/jolpica/jolpica-f1), stores it raw in Postgres, and (work in progress) models it with dbt into a star schema for a public Streamlit dashboard.

> **Status: work in progress.** The extraction layer and the Bronze load are finished and covered by tests. The dbt transformations, CI and dashboard are still being built (see [Roadmap](#roadmap)).

## Purpose

This project has two goals:

1. **A free, public F1 dashboard** for the 2026 season, kept up to date automatically after every race.
2. **A hands-on way to learn modern data engineering.** I built it to practice designing ELT pipelines end to end: reliable API extraction, incremental and idempotent loading, testing, dbt modelling, CI and scheduled orchestration. I'm a first-year Data Analytics student at the Prague University of Economics and Business (VŠE FIS), and this is the first of three planned portfolio projects.

## Architecture

```
Jolpica-F1 API
      │  requests + tenacity (retry, throttling)
      ▼
┌─────────────┐   raw JSONB payloads, UPSERT per (season, round)
│   Bronze    │   Neon Postgres
└──────┬──────┘
       │  dbt Core                                  (in progress)
       ▼
┌─────────────┐
│ Silver/Gold │   star schema: dimensions + fact tables
└──────┬──────┘
       │
       ▼
  Streamlit dashboard                               (planned)

Orchestration: GitHub Actions, daily cron             (planned)
```

Bronze keeps the API responses untouched (`season`, `round`, `payload` as JSONB, `_loaded_at`), so the downstream models can be rebuilt at any time without calling the API again.

## What is implemented

- **API client** (`extraction/client.py`) with:
  - exponential backoff via `tenacity`, applied only to transient failures (timeouts, connection errors, HTTP 408, 429 and 5xx)
  - a custom exception hierarchy that separates retryable from non-retryable errors (other 4xx, invalid JSON)
  - request throttling to stay under the API rate limits
  - a lightweight `HEAD` preflight check (`test_connection`) before a run starts
- **Incremental loading** (`extraction/extract.py`, `extraction/db_utils.py`):
  - watermark of the last loaded round plus a configurable lookback window, so late corrections to recent races are picked up
  - idempotent UPSERT (`ON CONFLICT (season, round) DO UPDATE ... WHERE payload IS DISTINCT FROM EXCLUDED.payload`), so `_loaded_at` changes only when the data really changed
  - a failure in one endpoint or round does not stop the rest of the run
- **Tests** (`pytest`):
  - unit tests of the client's retry and error classification using the `responses` library to mock HTTP
  - integration tests of the load logic against a real Postgres instance, isolated in a separate `test` schema that is dropped after each test

## Design decisions

| Decision | Why |
|---|---|
| ELT, not ETL | Raw payloads stay in the database, so transformations can be changed and replayed without re-fetching. |
| JSONB in Bronze | The API schema can change without breaking ingestion. Parsing happens in the dbt layer. |
| UPSERT with `IS DISTINCT FROM` | Re-running the pipeline is safe, and unchanged rows are not rewritten. |
| Watermark + lookback | Cheap incremental runs that still catch corrections to recent rounds. |
| Retry only transient errors | Retrying a 404 or malformed response wastes the rate limit and hides real bugs. |
| Pandas, not Spark | The data volume is small. Spark is reserved for a later project. |

## Tech stack

Python · requests · tenacity · SQLAlchemy · Neon (Postgres) · pytest · dbt Core (in progress) · GitHub Actions (planned) · Streamlit (planned) · uv

## Repository structure

```
extraction/
├── client.py        # Jolpica API client (retry, throttling, errors)
├── config.py        # constants (URLs, timeouts, retry settings, table names)
├── extract.py       # incremental extraction logic
├── db_utils.py      # table creation and UPSERT loading
└── tests/
    ├── test_client.py
    └── test_extract.py
pyproject.toml
```

## Getting started

Requirements: Python 3.14, [uv](https://docs.astral.sh/uv/), and a Postgres database (the project uses a free [Neon](https://neon.tech) instance).

```bash
git clone https://github.com/MZemik/f1-data-pipeline.git
cd f1-data-pipeline
uv sync
cp .env.example .env     # then set DATABASE_URL
```

Run the extraction:

```bash
uv run python extraction/extract.py
```

Run the tests:

```bash
uv run pytest extraction/tests/ -v
```

The integration tests connect to the database from `DATABASE_URL` but only create and drop the `test` schema. They never touch the Bronze schema.

## Roadmap

- [x] API client with retry, error classification and throttling
- [x] Bronze layer: incremental extraction and idempotent UPSERT
- [x] Unit and integration tests
- [ ] dbt: Silver models (parsing JSONB into typed tables) with tests and documentation
- [ ] dbt: Gold star schema (dimensions + fact tables, including sprint results)
- [ ] CI for Python: run `pytest` on every push and pull request (GitHub Actions, Postgres service container)
- [ ] CI for dbt: run `dbt build` on every pull request
- [ ] Scheduled pipeline: daily cron that only does work on the days after a race
- [ ] Gap-filling check for rounds missing from Bronze
- [ ] Public Streamlit dashboard

## Data source

Data comes from the [Jolpica-F1 API](https://github.com/jolpica/jolpica-f1), the community successor of the Ergast API. The pipeline respects its rate limits (4 requests per second, 500 per hour).