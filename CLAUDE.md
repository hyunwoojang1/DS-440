# CLAUDE.md — MHIDSS Project Guide

## Project Overview
Multi-Horizon Investment Decision Support System.
Integrates Macro (FRED), Fundamental (WRDS), and Technical data to produce
Entry Scores (0–100) across Short / Mid / Long investment horizons.

## How to Run
```bash
# Install dependencies
pip install -e ".[dev]"

# Configure environment variables
cp .env.example .env
# Fill in FRED_API_KEY, WRDS_USERNAME, WRDS_PASSWORD in the .env file

# Run
python main.py run --ticker SPY --format json,html

# Tests
pytest tests/unit/
pytest tests/integration/  # requires FRED_API_KEY
```

## Architecture
```
config/     - env vars, FRED series IDs, WRDS fields, weight matrices
data/       - data fetchers (FRED, WRDS, Technical), Parquet cache, data models
engine/     - normalizers (MinMax/ZScore/Percentile), scorers, horizon aggregators, EntryScoreEngine
utils/      - date utilities, math helpers, validation, logging, retry
reports/    - JSON/CSV/HTML report generation
main.py     - CLI entry point (typer)
```

## Core Principles
- **No look-ahead bias**: `BaseNormalizer.fit()` must only use data before `as_of_date`
- **Immutability**: never mutate DataFrames in place — always return new objects
- **Abstraction**: data providers accessed only through the `BaseFetcher` interface
- **Insufficient data**: never assign a zero score — flag as `INSUFFICIENT_DATA` then redistribute weights

## Weight Matrix (config/weights.py)
| Group | Short (1-4W) | Mid (1-6M) | Long (6-24M) |
|-------|-------------|------------|--------------|
| Macro | 0.20 | 0.30 | 0.40 |
| Fundamental | 0.10 | 0.30 | 0.35 |
| Technical | 0.70 | 0.40 | 0.25 |

## Commands
- `/tdd` — start TDD cycle when implementing a new feature
- `/code-review` — review changes
- `/build-fix` — fix dependency or type errors

## Key Files
- `engine/normalizers/base.py` — fit/transform contract (architecture core)
- `config/weights.py` — weight matrix (core domain knowledge)
- `engine/entry_score.py` — full pipeline orchestrator
- `data/fetchers/base.py` — data provider swap interface
- `data/cache/disk_cache.py` — Parquet TTL cache
