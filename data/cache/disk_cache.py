"""Parquet-based disk cache (Polars, TTL-enforced)."""

from datetime import datetime, timedelta
from pathlib import Path

import polars as pl


class DiskCache:
    def __init__(self, cache_dir: Path, ttl_hours: int = 24) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(":", "_").replace(" ", "_")
        return self.cache_dir / f"{safe}.parquet"

    def get(self, key: str) -> pl.DataFrame | None:
        path = self._path(key)
        if not path.exists():
            return None
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        if age > self.ttl:
            path.unlink(missing_ok=True)
            return None
        try:
            return pl.read_parquet(path)
        except Exception:
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, df: pl.DataFrame) -> None:
        self._path(key).parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(self._path(key))

    def invalidate(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def clear_expired(self) -> int:
        removed = 0
        for p in self.cache_dir.glob("*.parquet"):
            age = datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)
            if age > self.ttl:
                p.unlink(missing_ok=True)
                removed += 1
        return removed
