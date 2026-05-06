"""Helpers de tempo e business_date."""
from __future__ import annotations
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from .config import settings

APP_TZ = ZoneInfo(settings.timezone)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return datetime.now(APP_TZ)


def to_business_date(dt: datetime | None = None) -> date:
    """Calcula o dia operacional considerando o cutoff (ex.: 04h)."""
    dt = (dt or now_local()).astimezone(APP_TZ)
    if dt.hour < settings.business_day_cutoff_hour:
        dt = dt - timedelta(days=1)
    return dt.date()
