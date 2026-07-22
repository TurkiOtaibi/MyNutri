from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings, validate_runtime_configuration


def calendar_timezone() -> ZoneInfo:
    settings = get_settings()
    validate_runtime_configuration(settings)
    return ZoneInfo(settings.calendar_timezone)


@dataclass(frozen=True)
class DiaryCalendarAuthority:
    current_diary_date: date
    calendar_timezone: str
    next_rollover_at: datetime


def diary_calendar_authority(now: datetime | None = None) -> DiaryCalendarAuthority:
    timezone = calendar_timezone()
    if now is not None and now.tzinfo is None:
        raise ValueError("Diary calendar authority requires an aware datetime.")
    current = now.astimezone(timezone) if now is not None else datetime.now(timezone)
    current_date = current.date()
    next_midnight = datetime.combine(current_date + timedelta(days=1), time.min, timezone)
    return DiaryCalendarAuthority(
        current_diary_date=current_date,
        calendar_timezone=timezone.key,
        next_rollover_at=next_midnight,
    )


def current_diary_date(now: datetime | None = None) -> date:
    return diary_calendar_authority(now).current_diary_date


def next_diary_date(now: datetime | None = None) -> date:
    return current_diary_date(now) + timedelta(days=1)
