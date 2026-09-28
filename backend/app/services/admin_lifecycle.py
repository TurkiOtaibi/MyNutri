"""Principal-locked account lifecycle; private facts never cross the purge boundary."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import (
    DiaryEntry,
    IdempotencyRecord,
    LabResult,
    Principal,
    PrincipalRole,
    PrincipalStatus,
    Profile,
    TargetPlan,
)
from app.services.admin_auth import AdminAuthError, AdminAuthGateway, AdminIdentity

logger = logging.getLogger(__name__)


class LifecycleError(Exception):
    def __init__(self, status_code: int, code: str, message_ar: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message_ar = message_ar
        super().__init__(code)


def _creation_incomplete() -> LifecycleError:
    return LifecycleError(409, "CREATION_INCOMPLETE", "تعذر إكمال إنشاء المستخدم. أعد المحاولة.")


def _duplicate_email() -> LifecycleError:
    return LifecycleError(409, "DUPLICATE_EMAIL", "هذا البريد الإلكتروني مستخدم بالفعل.")


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


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _next_second(value: datetime) -> datetime:
    return _utc(value).replace(microsecond=0) + timedelta(seconds=1)


def reset_account_password(
    session: Session,
    admin_id: UUID,
    principal_id: UUID,
    password: str,
    gateway: AdminAuthGateway,
    now: datetime,
) -> None:
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if row.status not in {PrincipalStatus.active, PrincipalStatus.disabled} or row.auth_user_id is None:
        raise _creation_incomplete()
    auth_id = row.auth_user_id
    row.sessions_valid_after = _next_second(now)
    row.updated_at = now
    session.add(row)
    session.commit()
    gateway.reset_password(auth_id, password)


def set_account_enabled(
    session: Session, admin_id: UUID, principal_id: UUID, enabled: bool, now: datetime
) -> Principal:
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if row.status not in {PrincipalStatus.active, PrincipalStatus.disabled}:
        raise _creation_incomplete()
    row.status = PrincipalStatus.active if enabled else PrincipalStatus.disabled
    row.sessions_valid_after = _next_second(now)
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


def _is_retired(session: Session, auth_id: UUID) -> bool:
    return session.exec(
        select(Principal.id).where(Principal.retired_auth_user_id == auth_id)
    ).first() is not None


def reconcile_retired_identity(
    session: Session, auth_id: UUID, gateway: AdminAuthGateway
) -> bool:
    """Return true only after a retired identity is verified absent."""
    if not _is_retired(session, auth_id):
        return False
    gateway.delete_user(auth_id)
    if gateway.get_user_by_id(auth_id) is not None:
        raise AdminAuthError("identity_present")
    return True


def _reconcile_rows(
    session: Session, rows: list[UUID], gateway: AdminAuthGateway
) -> dict[str, int]:
    failures: dict[str, int] = {}
    for auth_id in rows:
        try:
            reconcile_retired_identity(session, auth_id, gateway)
        except AdminAuthError as error:
            failures[error.kind] = failures.get(error.kind, 0) + 1
    for kind, count in failures.items():
        logger.warning("retired identity reconciliation failed: type=%s count=%s", kind, count)
    return {"checked": len(rows), "failed": sum(failures.values())}


def reconcile_recent_tombstones(
    session: Session,
    gateway: AdminAuthGateway,
    now: datetime,
    *,
    limit: int = 100,
) -> dict[str, int]:
    rows = session.exec(
        select(Principal.id, Principal.retired_auth_user_id)
        .where(
            Principal.status == PrincipalStatus.deleted,
            Principal.deleted_at >= now - timedelta(days=30),
            Principal.retired_auth_user_id.is_not(None),
        )
        .order_by(Principal.updated_at, Principal.id)
        .limit(limit)
    ).all()
    outcome = _reconcile_rows(session, [row[1] for row in rows], gateway)
    if rows:
        # Track attempts on the scrubbed tombstone so the next bounded list
        # trigger can reach identities beyond the first page, including retries.
        session.exec(
            update(Principal)
            .where(Principal.id.in_([row[0] for row in rows]))
            .values(updated_at=now)
        )
        session.commit()
    return outcome


def reconcile_all_retired(
    session: Session, gateway: AdminAuthGateway, *, batch_size: int = 100
) -> dict[str, int]:
    total = {"checked": 0, "failed": 0}
    cursor: UUID | None = None
    while True:
        statement = (
            select(Principal.id, Principal.retired_auth_user_id)
            .where(
                Principal.status == PrincipalStatus.deleted,
                Principal.retired_auth_user_id.is_not(None),
            )
            .order_by(Principal.id)
            .limit(batch_size)
        )
        if cursor is not None:
            statement = statement.where(Principal.id > cursor)
        rows = session.exec(statement).all()
        if not rows:
            break
        outcome = _reconcile_rows(session, [row[1] for row in rows], gateway)
        total["checked"] += outcome["checked"]
        total["failed"] += outcome["failed"]
        cursor = rows[-1][0]
    return total


def _resolve_duplicate(
    session: Session, email: str, expected_id: UUID, gateway: AdminAuthGateway
) -> AdminIdentity | None:
    identity = gateway.find_user_by_email(email)
    if identity is None:
        raise AdminAuthError("unavailable")
    if identity.id == expected_id:
        return identity
    if _is_retired(session, identity.id):
        reconcile_retired_identity(session, identity.id, gateway)
        return None
    raise _duplicate_email()


def create_account(
    session: Session,
    admin_id: UUID,
    email: str,
    display_name: str,
    password: str,
    idempotency_key: str,
    gateway: AdminAuthGateway,
    now: datetime,
    timeout_seconds: int,
) -> Principal:
    if not 1 <= timeout_seconds <= 60:
        raise AdminAuthError("unavailable")
    normalized_email = email.strip().lower()
    normalized_name = " ".join(display_name.split())
    _admin(session, admin_id)
    row = session.exec(
        select(Principal)
        .where(Principal.creation_idempotency_key == idempotency_key)
        .with_for_update()
    ).one_or_none()
    if row is None:
        if session.exec(
            select(Principal.id).where(Principal.email == normalized_email)
        ).first() is not None:
            raise _duplicate_email()
        row = Principal(
            auth_user_id=uuid4(),
            email=normalized_email,
            display_name=normalized_name,
            status=PrincipalStatus.provisioning,
            creation_idempotency_key=idempotency_key,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise _duplicate_email() from error
    elif row.email != normalized_email or row.display_name != normalized_name:
        raise _duplicate_email()
    if row.status == PrincipalStatus.active:
        return row
    if row.status != PrincipalStatus.provisioning or row.auth_user_id is None:
        raise _creation_incomplete()

    row = _target(session, admin_id, row.id)
    if row.status != PrincipalStatus.provisioning:
        raise _creation_incomplete()
    row.identity_requested_at = now
    row.updated_at = now
    session.add(row)
    session.commit()
    auth_id = row.auth_user_id
    assert auth_id is not None

    identity = gateway.get_user_by_id(auth_id)
    identity_preexisting = identity is not None
    if identity is None:
        try:
            identity = gateway.create_user(auth_id, normalized_email, password)
        except AdminAuthError as error:
            if error.kind != "duplicate_email":
                raise
            identity = _resolve_duplicate(session, normalized_email, auth_id, gateway)
            if identity is None:
                identity = gateway.create_user(auth_id, normalized_email, password)
            else:
                identity_preexisting = True
    if identity.id != auth_id or identity.email is None or identity.email.lower() != normalized_email:
        raise AdminAuthError("identity_mismatch")

    row = _target(session, admin_id, row.id)
    if row.status == PrincipalStatus.active and row.auth_user_id == auth_id:
        session.rollback()
        return row
    if row.status != PrincipalStatus.provisioning:
        raise _creation_incomplete()
    if identity_preexisting:
        # A prior create may have completed after its response was lost. Apply the
        # password submitted on this retry while the Principal remains locked out.
        gateway.reset_password(auth_id, password)
    row.status = PrincipalStatus.active
    row.updated_at = now
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _purge_private_rows(session: Session, principal_id: UUID) -> None:
    for model in (DiaryEntry, LabResult, IdempotencyRecord, TargetPlan, Profile):
        session.exec(delete(model).where(model.principal_id == principal_id))


def delete_account(
    session: Session,
    admin_id: UUID,
    principal_id: UUID,
    gateway: AdminAuthGateway,
    now: datetime,
    timeout_seconds: int,
    confirmation_email: str | None = None,
) -> Principal:
    _admin(session, admin_id)
    row = _target(session, admin_id, principal_id)
    if confirmation_email is not None and row.status != PrincipalStatus.deleting:
        if row.email is None or confirmation_email.strip().lower() != row.email.lower():
            raise LifecycleError(
                422,
                "DELETE_EMAIL_MISMATCH",
                "البريد الإلكتروني المدخل لا يطابق بريد المستخدم.",
            )
    if row.status == PrincipalStatus.deleted:
        return row
    if row.status == PrincipalStatus.provisioning and row.identity_requested_at is not None:
        lease = timedelta(seconds=max(300, 10 * timeout_seconds))
        if now <= _utc(row.identity_requested_at) + lease:
            raise _creation_incomplete()
    if row.status != PrincipalStatus.deleting:
        row.status = PrincipalStatus.deleting
        row.deletion_started_at = now
        row.updated_at = now
        session.add(row)
        session.commit()

    row = _target(session, admin_id, principal_id)
    _purge_private_rows(session, principal_id)
    session.commit()

    auth_id = row.auth_user_id
    if auth_id is not None:
        gateway.delete_user(auth_id)
        if gateway.get_user_by_id(auth_id) is not None:
            raise AdminAuthError("identity_present")

    row = _target(session, admin_id, principal_id)
    if row.status == PrincipalStatus.deleted:
        return row
    row.auth_user_id = None
    row.retired_auth_user_id = auth_id
    row.email = None
    row.display_name = None
    row.status = PrincipalStatus.deleted
    row.deleted_at = now
    row.updated_at = now
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
