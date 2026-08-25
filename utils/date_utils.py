"""Date processing utilities."""

from datetime import date, timedelta


def years_before(reference: str, years: int) -> str:
    ref = date.fromisoformat(reference)
    return date(ref.year - years, ref.month, ref.day).isoformat()


def days_before(reference: str, days: int) -> str:
    return (date.fromisoformat(reference) - timedelta(days=days)).isoformat()


def trading_days_between(start: str, end: str) -> int:
    """Approximate trading day count calculation (excludes weekends)."""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    delta = (e - s).days
    weeks = delta // 7
    remainder = delta % 7
    # Based on start-date weekday (0=Monday)
    weekday = s.weekday()
    extra_weekdays = sum(1 for i in range(remainder) if (weekday + i) % 7 < 5)
    return weeks * 5 + extra_weekdays
