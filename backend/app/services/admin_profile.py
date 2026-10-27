"""The explicitly authorized, sex-only exception to Admin monitoring."""

from uuid import UUID

from sqlmodel import Session, select

from app.models import PrincipalStatus, Profile, Sex
from app.services.admin_lifecycle import LifecycleError, _admin, _target


def correct_profile_sex(session: Session, admin_id: UUID, target_id: UUID, sex: Sex) -> None:
    # Match the Principal -> Profile locking order of owner Target Plan writes.
    _admin(session, admin_id)
    target = _target(session, admin_id, target_id)
    if target.status not in {PrincipalStatus.active, PrincipalStatus.disabled}:
        raise LifecycleError(409, "ACCOUNT_STATE_CONFLICT", "تعذر حفظ تغييرات المستخدم. حاول مرة أخرى.")
    profile = session.exec(
        select(Profile).where(Profile.principal_id == target_id).with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if profile is None:
        raise LifecycleError(409, "PROFILE_REQUIRED", "لا يمكن تصحيح الجنس قبل حفظ الملف الشخصي للمستخدم.")
    # No timestamp, preferences, saved calculation or private fact is rewritten.
    profile.sex = sex
    session.add(profile)
    session.commit()
