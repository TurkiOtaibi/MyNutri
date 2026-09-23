"""Read-only demographic checks shared by preview and locked Profile writes."""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.calendar import age_on
from app.models import LabResult, Profile, Sex
from app.nutrition_rules.calculation import CalculationError


class ProfileConstraintError(CalculationError):
    """Profile domain rejection, translated to the existing write error envelope."""


def validate_profile_constraints(
    session: Session,
    principal_id: UUID,
    current: Profile | None,
    proposed_sex: Sex,
    proposed_dob: date,
) -> None:
    """Call under Principal/Profile locks when authorizing a mutation."""
    if current is None:
        return
    if proposed_sex != current.sex:
        raise ProfileConstraintError(
            "PROFILE_SEX_IMMUTABLE",
            "لا يمكن تعديل الجنس بعد حفظ الملف الشخصي.",
            "sex",
        )
    if proposed_dob == current.birth_date:
        return
    earliest_date = session.exec(
        select(func.min(LabResult.test_date)).where(LabResult.principal_id == principal_id)
    ).one()
    if earliest_date is not None and age_on(proposed_dob, earliest_date) < 18:
        raise ProfileConstraintError(
            "LABS_ADULT_HISTORY_REQUIRED",
            "لا يمكن تعديل تاريخ الميلاد لأنه يجعل نتائج تحاليل مسجلة قبل عمر 18 سنة.",
            "birth_date",
        )
