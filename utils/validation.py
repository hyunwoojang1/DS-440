"""Pydantic-based runtime data validation."""

from pydantic import BaseModel, field_validator


class IndicatorScore(BaseModel):
    indicator_id: str
    raw_value: float | None
    normalized_score: float | None

    @field_validator("normalized_score")
    @classmethod
    def check_range(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError(f"Score must be in the 0-100 range: {v}")
        return v


class EntryScoreReport(BaseModel):
    ticker: str
    as_of_date: str
    short_entry_score: float
    mid_entry_score: float
    long_entry_score: float
