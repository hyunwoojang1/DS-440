"""Macro data snapshot model."""

from dataclasses import dataclass, field


@dataclass
class MacroSnapshot:
    as_of_date: str
    values: dict[str, float] = field(default_factory=dict)
    source_dates: dict[str, str] = field(default_factory=dict)  # Actual data date per indicator
