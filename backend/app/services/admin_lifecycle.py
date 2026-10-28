"""Principal-locked account lifecycle; private facts never cross the purge boundary."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import (
    AuthSession,
    DiaryEntry,
    IdempotencyRecord,
    LabResult,
    Principal,
    PrincipalRole,
    PrincipalStatus,
    Profile,
    TargetPlan,
)
from app.services.internal_auth import revoke_sessions
from app.core.credentials import hash_password, normalize_username, validate_password, verify_password


class LifecycleError(Exception):
    def __init__(self, status_code: int, code: str, message_ar: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message_ar = message_ar
        super().__init__(code)


def _creation_incomplete() -> LifecycleError:
    return LifecycleError(409, "CREATION_INCOMPLETE", "تعذر إكمال إنشاء المستخدم. أعد المحاولة.")


def _invalid_target() -> LifecycleError:
    return LifecycleError(
        403, "ADMIN_ACCOUNT_FORBIDDEN", "لا يمكن تعطيل حساب المشرف أو حذفه أو تغيير دوره."
    )


def _admin(session: Session, admin_id: UUID) -> Principal:
    row = session.exec(
        select(Principal).where(Principal.id == admin_id).with_for_update()
    ).one_or_none()
    if row is None or row.role != PrincipalRole.admin or row.status != PrincipalStatus.active:
        raise LifecycleError(403, "FORBIDDEN", "ليس لديك صلاحية لتنفيذ هذا الإجراء.")
    return row


def _target(session: Session, admin_id: UUID, principal_id: UUID) -> Principal:
    if principal_id == admin_id:
        raise _invalid_target()
    row = session.exec(
        select(Principal).where(Principal.id == principal_id).with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if row is None:
        raise LifecycleError(404, "RESOURCE_NOT_FOUND", "المورد غير موجود.")
    if row.role == PrincipalRole.admin:
        raise _invalid_target()
    return row


def reset_account_password(
    session: Session,
    admin_id: UUID,
    principal_id: UUID,
    password: str,
    now: datetime,
) -> None:
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if row.status not in {PrincipalStatus.active, PrincipalStatus.disabled} or row.password_hash is None:
        raise _creation_incomplete()
    try:
        validate_password(password)
    except ValueError as error:
        raise LifecycleError(422, "INVALID_PASSWORD", str(error)) from None
    row.password_hash = hash_password(password)
    revoke_sessions(session, row.id, now)
    row.updated_at = now
    row.must_change_password = False
    row.failed_login_count = 0
    row.locked_at = None
    session.add(row)
    session.commit()


def set_account_enabled(
    session: Session, admin_id: UUID, principal_id: UUID, enabled: bool, now: datetime
) -> Principal:
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if row.status not in {PrincipalStatus.active, PrincipalStatus.disabled}:
        raise _creation_incomplete()
    if enabled:
        row.disabled_at = None
    elif row.status != PrincipalStatus.disabled:
        row.disabled_at = now
    row.status = PrincipalStatus.active if enabled else PrincipalStatus.disabled
    revoke_sessions(session, row.id, now)
    row.updated_at = now
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def edit_display_name(
    session: Session, admin_id: UUID, principal_id: UUID, display_name: str, now: datetime
) -> Principal:
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if row.status not in {PrincipalStatus.active, PrincipalStatus.disabled}:
        raise _creation_incomplete()
    row.display_name = " ".join(display_name.split())
    row.updated_at = now
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_internal_account(
    session: Session,
    admin_id: UUID,
    username: str,
    display_name: str,
    password: str,
    idempotency_key: str,
    now: datetime,
) -> Principal:
    _admin(session, admin_id)
    try:
        normalized = normalize_username(username)
    except ValueError as error:
        raise LifecycleError(422, "INVALID_USERNAME", str(error)) from None
    try:
        validate_password(password)
    except ValueError as error:
        raise LifecycleError(422, "INVALID_PASSWORD", str(error)) from None
    name = " ".join(display_name.split())
    existing = session.exec(select(Principal).where(
        Principal.creation_idempotency_key == idempotency_key,
    ).with_for_update()).one_or_none()
    if existing is not None:
        # Never restore a deleted account or overwrite credentials after reset/change.
        if (existing.normalized_username == normalized and existing.display_name == name
                and existing.status in {PrincipalStatus.active, PrincipalStatus.disabled}
                and existing.password_hash is not None
                and verify_password(password, existing.password_hash)):
            return existing
        raise _creation_incomplete()
    if session.exec(select(Principal.id).where(
        Principal.normalized_username == normalized,
    )).first() is not None:
        raise LifecycleError(409, "DUPLICATE_USERNAME", "اسم المستخدم هذا مستخدم بالفعل.")
    row = Principal(
        username=username, normalized_username=normalized, display_name=name,
        password_hash=hash_password(password), must_change_password=True,
        role=PrincipalRole.user, status=PrincipalStatus.active,
        creation_idempotency_key=idempotency_key, created_at=now, updated_at=now,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise LifecycleError(409, "DUPLICATE_USERNAME", "اسم المستخدم هذا مستخدم بالفعل.") from error
    session.refresh(row)
    return row


def _purge_private_rows(session: Session, principal_id: UUID) -> None:
    for model in (AuthSession, DiaryEntry, LabResult, IdempotencyRecord, TargetPlan, Profile):
        session.exec(delete(model).where(model.principal_id == principal_id))


def _scrub_deleted_account(row: Principal, auth_id: UUID | None, now: datetime) -> None:
    row.auth_user_id = None
    row.retired_auth_user_id = auth_id
    row.email = None
    row.display_name = None
    row.username = None
    row.normalized_username = None
    row.password_hash = None
    row.must_change_password = False
    row.failed_login_count = 0
    row.locked_at = None
    row.last_login_at = None
    row.status = PrincipalStatus.deleted
    row.deleted_at = now
    row.updated_at = now


def delete_account(
    session: Session,
    admin_id: UUID,
    principal_id: UUID,
    now: datetime,
    confirmation_email: str | None = None,
    confirmation_username: str | None = None,
    require_confirmation: bool = False,
) -> Principal:
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if row.status == PrincipalStatus.deleted:
        return row
    if row.username is not None and (require_confirmation or confirmation_username is not None or confirmation_email is not None):
        if confirmation_username is None or confirmation_username.lower() != row.normalized_username:
            raise LifecycleError(422, "DELETE_USERNAME_MISMATCH", "اسم المستخدم المدخل لا يطابق هذا الحساب.")
    elif require_confirmation or confirmation_email is not None:
        if row.email is None or confirmation_email is None or confirmation_email.strip().lower() != row.email.lower():
            raise LifecycleError(
                422,
                "DELETE_EMAIL_MISMATCH",
                "البريد الإلكتروني المدخل لا يطابق بريد المستخدم.",
            )
    # Persist the admission barrier before destructive work. A failed purge must
    # never roll back the account's lockout or restore its sessions (BR-USM-044).
    row.status = PrincipalStatus.deleting
    row.deletion_started_at = row.deletion_started_at or now
    row.updated_at = now
    revoke_sessions(session, principal_id, now)
    session.add(row)
    session.commit()

    # Reacquire locks in the existing Admin -> target order in transaction two.
    # Another delete may have completed between transactions; that is a success.
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if row.status == PrincipalStatus.deleted:
        return row
    try:
        _purge_private_rows(session, principal_id)
        _scrub_deleted_account(row, row.auth_user_id or row.retired_auth_user_id, now)
        session.add(row)
        session.commit()
    except Exception:
        session.rollback()
        raise LifecycleError(
            503, "DELETION_INCOMPLETE",
            "تعذر إكمال حذف المستخدم. لا يستطيع الدخول الآن، ويمكنك إعادة المحاولة.",
        ) from None
    session.refresh(row)
    return row
