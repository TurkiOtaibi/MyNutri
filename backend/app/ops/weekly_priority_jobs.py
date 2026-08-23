from __future__ import annotations

import argparse
from datetime import timedelta
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.auth import PrincipalContext
from app.core.config import get_settings
from app.db.session import engine
from app.models import NutritionAnalysis, WeeklyPriorityRecommendation
from app.services.weekly_priorities import ensure_offer, evaluate_recommendation, process_due_goals


def evaluation_batch(
    *, limit: int, after: UUID | None = None, shadow: bool
) -> dict[str, int | str | None]:
    settings = get_settings()
    if shadow and not settings.weekly_priorities_shadow_v1:
        raise RuntimeError("WEEKLY_PRIORITIES_SHADOW_V1 must be explicitly enabled.")
    if shadow and (
        settings.weekly_priorities_display_enabled
        or settings.behavior_goal_offers_enabled
        or settings.behavior_goal_reminder_delivery_enabled
    ):
        raise RuntimeError(
            "Shadow evaluation requires display, offers, and delivery to remain disabled."
        )
    if not shadow and not (
        settings.weekly_priorities_display_enabled and settings.behavior_goal_offers_enabled
    ):
        raise RuntimeError("Offer evaluation requires display and offers to be explicitly enabled.")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    with Session(engine) as session:
        statement = (
            select(NutritionAnalysis.principal_id)
            .distinct()
            .order_by(NutritionAnalysis.principal_id)
            .limit(limit)
        )
        if after is not None:
            statement = statement.where(NutritionAnalysis.principal_id > after)
        principal_ids = list(session.exec(statement).all())
    created = failed = offers = 0
    for principal_id in principal_ids:
        with Session(engine) as session:
            try:
                recommendation = evaluate_recommendation(
                    session, PrincipalContext(principal_id=principal_id)
                )
                created += 1
                if not shadow and ensure_offer(
                    session, PrincipalContext(principal_id=principal_id), recommendation
                ):
                    offers += 1
            except Exception:
                session.rollback()
                failed += 1
    return {
        "processed": len(principal_ids),
        "created_or_replayed": created,
        "offers_created_or_replayed": offers,
        "failed": failed,
        "next_after": str(principal_ids[-1]) if len(principal_ids) == limit else None,
    }


def shadow_batch(*, limit: int, after: UUID | None = None) -> dict[str, int | str | None]:
    return evaluation_batch(limit=limit, after=after, shadow=True)


def launch_gate_report() -> dict[str, int | bool | str | None]:
    """Return only non-identifying aggregate evidence for launch review."""
    with Session(engine) as session:
        eligible = session.exec(
            select(func.count()).select_from(WeeklyPriorityRecommendation).where(
                WeeklyPriorityRecommendation.status == "selected"
            )
        ).one()
        dates = sorted(
            {
                created.date()
                for created in session.exec(
                    select(WeeklyPriorityRecommendation.created_at).where(
                        WeeklyPriorityRecommendation.status == "selected"
                    )
                ).all()
            }
        )
    longest = current = 0
    previous = None
    for observed in dates:
        current = current + 1 if previous and observed == previous + timedelta(days=1) else 1
        longest = max(longest, current)
        previous = observed
    first, last = (dates[0] if dates else None), (dates[-1] if dates else None)
    return {
        "eligible_evaluations": int(eligible),
        "consecutive_shadow_days": longest,
        "first_iso_week": first.isocalendar().year
        and f"{first.isocalendar().year}-W{first.isocalendar().week:02d}"
        if first
        else None,
        "last_iso_week": last.isocalendar().year
        and f"{last.isocalendar().year}-W{last.isocalendar().week:02d}"
        if last
        else None,
        "launch_gate_met": longest >= 28 and int(eligible) >= 1000,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded PLAN 033 shadow and goal jobs.")
    parser.add_argument("mode", choices=["shadow", "offers", "due", "report"])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--after", type=UUID)
    args = parser.parse_args()
    if args.mode == "shadow":
        result = shadow_batch(limit=args.limit, after=args.after)
    elif args.mode == "offers":
        result = evaluation_batch(limit=args.limit, after=args.after, shadow=False)
    elif args.mode == "due":
        with Session(engine) as session:
            result = process_due_goals(session, limit=args.limit)
    else:
        result = launch_gate_report()
    print(result)


if __name__ == "__main__":
    main()
