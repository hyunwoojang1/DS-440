"""Scorer base interface."""

from abc import ABC, abstractmethod


class BaseScorer(ABC):
    @abstractmethod
    def score(self, raw_values: dict[str, float], as_of_date: str) -> dict[str, float]:
        """Receives raw indicator values and returns a dict of [0, 100] scores per indicator."""
        ...
