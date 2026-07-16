from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings, validate_runtime_configuration


def calendar_timezone() -> ZoneInfo:
    settings = get_settings()
    validate_runtime_configuration(settings)
    return ZoneInfo(settings.calendar_timezone)


def current_diary_date(now: datetime | None = None) -> date:
    timezone = calendar_timezone()
    current = now.astimezone(timezone) if now is not None else datetime.now(timezone)
    return current.date()


def next_diary_date(now: datetime | None = None) -> date:
    return current_diary_date(now) + timedelta(days=1)
