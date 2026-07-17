from datetime import date, timedelta

from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import DiaryEntry
from app.schemas import DaySummary, WeekSummary
from app.services.diary import add_totals, empty_totals, totals_for_entry
from app.services.profile import get_profile, to_target_response


def sunday_start(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)


def weekly_summary(session: Session, principal: PrincipalContext, start: date) -> WeekSummary:
    week_start = sunday_start(start)
    week_end = week_start + timedelta(days=6)
    entries = session.exec(
        select(DiaryEntry).where(
            DiaryEntry.principal_id == principal.principal_id,
            DiaryEntry.entry_date >= week_start,
            DiaryEntry.entry_date <= week_end,
        )
    ).all()

    targets = None
    profile = get_profile(session, principal)
    if profile is not None:
        targets = to_target_response(profile)

    days: list[DaySummary] = []
    weekly_totals = empty_totals()
    for offset in range(7):
        current = week_start + timedelta(days=offset)
        totals = empty_totals()
        for entry in entries:
            if entry.entry_date == current:
                totals = add_totals(totals, totals_for_entry(entry))
        weekly_totals = add_totals(weekly_totals, totals)
        days.append(DaySummary(date=current, totals=totals, targets=targets))

    return WeekSummary(start=week_start, end=week_end, days=days, weekly_totals=weekly_totals, targets=targets)
