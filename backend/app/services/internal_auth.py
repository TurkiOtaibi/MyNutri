"""Principal-serialized internal authentication and opaque bearer sessions."""

import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import update
from sqlmodel import Session, select

from app.core.credentials import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    normalize_username,
    verify_password,
)
from app.models import AuthSession, Principal, PrincipalRole, PrincipalStatus

SESSION_LIFETIME = timedelta(days=30)
TOKEN_PREFIX = "mn1_"
LOGIN_MESSAGE = "تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى."
DISABLED_MESSAGE = "حسابك موقوف. تواصل مع المشرف."
EXPIRED_MESSAGE = "انتهت جلستك. سجّل الدخول مرة أخرى."


class AuthError(Exception):
    def __init__(self, code: str, message_ar: str, status_code: int = 401):
        super().__init__(code)
        self.code, self.message_ar, self.status_code = code, message_ar, status_code


@dataclass(frozen=True)
class LoginResult:
    token: str = field(repr=False)
    principal: Principal = field(repr=False)
    expires_at: datetime


def utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def lock_principal(session: Session, principal_id: UUID) -> Principal | None:
    return session.exec(
        select(Principal)
        .where(Principal.id == principal_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()


def revoke_sessions(
    session: Session, principal_id: UUID, now: datetime, *, except_id: UUID | None = None
) -> None:
    statement = update(AuthSession).where(
        AuthSession.principal_id == principal_id, AuthSession.revoked_at.is_(None)
    )
    if except_id is not None:
        statement = statement.where(AuthSession.id != except_id)
    session.execute(statement.values(revoked_at=now))


def _locked(principal: Principal) -> AuthError:
    if principal.role == PrincipalRole.admin:
        return AuthError(
            "ADMIN_LOCKED", "تم قفل الحساب بعد 5 محاولات دخول فاشلة. حاول مرة أخرى بعد 30 دقيقة."
        )
    return AuthError(
        "USER_LOCKED", "تم قفل الحساب بعد 5 محاولات دخول فاشلة. تواصل مع المشرف لفتحه."
    )


def login(session: Session, username: str, password: str, now: datetime) -> LoginResult:
    try:
        normalized = normalize_username(username)
    except ValueError:
        normalized = None
    principal = None
    if normalized is not None:
        principal = session.exec(
            select(Principal)
            .where(Principal.normalized_username == normalized)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()
    matched = verify_password(
        password,
        principal.password_hash if principal and principal.password_hash else DUMMY_PASSWORD_HASH,
    )
    if principal is None:
        session.rollback()
        raise AuthError("LOGIN_FAILED", LOGIN_MESSAGE)
    if principal.status != PrincipalStatus.active:
        session.rollback()
        if matched and principal.status == PrincipalStatus.disabled:
            raise AuthError("ACCOUNT_DISABLED", DISABLED_MESSAGE)
        raise AuthError("LOGIN_FAILED", LOGIN_MESSAGE)
    if principal.locked_at is not None:
        if principal.role == PrincipalRole.admin and now >= utc(principal.locked_at) + timedelta(
            minutes=30
        ):
            principal.locked_at = None
            principal.failed_login_count = 0
        else:
            failure = _locked(principal)
            session.rollback()
            raise failure
    if not matched:
        principal.failed_login_count += 1
        if principal.failed_login_count >= 5:
            principal.locked_at = now
        failure = (
            _locked(principal) if principal.locked_at else AuthError("LOGIN_FAILED", LOGIN_MESSAGE)
        )
        session.add(principal)
        session.commit()
        raise failure
    principal.failed_login_count = 0
    principal.locked_at = None
    principal.last_login_at = now
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires = now + SESSION_LIFETIME
    session.add(
        AuthSession(
            principal_id=principal.id,
            token_hash=token_digest(token),
            created_at=now,
            last_used_at=now,
            expires_at=expires,
        )
    )
    session.add(principal)
    session.commit()
    return LoginResult(token, principal, expires)


def admit_session(session: Session, token: str, now: datetime) -> tuple[Principal, AuthSession]:
    if re.fullmatch(r"mn1_[A-Za-z0-9_-]{43}", token) is None:
        raise AuthError("INVALID_CREDENTIAL", EXPIRED_MESSAGE)
    # Discover ownership without taking a session lock: all writers lock Principal first.
    owner = session.exec(
        select(AuthSession.principal_id).where(AuthSession.token_hash == token_digest(token))
    ).one_or_none()
    principal = lock_principal(session, owner) if owner else None
    if principal is None:
        session.rollback()
        raise AuthError("INVALID_CREDENTIAL", EXPIRED_MESSAGE)
    if principal.status != PrincipalStatus.active:
        disabled = principal.status == PrincipalStatus.disabled
        revoke_sessions(session, principal.id, now)
        session.commit()
        raise AuthError(
            "ACCOUNT_DISABLED" if disabled else "INVALID_CREDENTIAL",
            DISABLED_MESSAGE if disabled else EXPIRED_MESSAGE,
        )
    current = session.exec(
        select(AuthSession)
        .where(AuthSession.token_hash == token_digest(token))
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if current is None or current.revoked_at is not None or utc(current.expires_at) <= now:
        session.rollback()
        raise AuthError("INVALID_CREDENTIAL", EXPIRED_MESSAGE)
    current.last_used_at = now
    current.expires_at = now + SESSION_LIFETIME
    session.add(current)
    session.commit()
    return principal, current


def logout(session: Session, principal_id: UUID, session_id: UUID, now: datetime) -> None:
    lock_principal(session, principal_id)
    session.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.principal_id == principal_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    session.commit()


def change_password(
    session: Session,
    principal_id: UUID,
    session_id: UUID,
    current_password: str,
    new_password: str,
    now: datetime,
) -> None:
    principal = lock_principal(session, principal_id)
    current = session.exec(
        select(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.principal_id == principal_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if (
        principal is None
        or principal.status != PrincipalStatus.active
        or current is None
        or current.revoked_at is not None
        or utc(current.expires_at) <= now
    ):
        raise AuthError("INVALID_CREDENTIAL", EXPIRED_MESSAGE)
    if principal.password_hash is None or not verify_password(
        current_password, principal.password_hash
    ):
        raise AuthError("CURRENT_PASSWORD_INCORRECT", "كلمة المرور الحالية غير صحيحة.", 422)
    try:
        encoded = hash_password(new_password)
    except ValueError as error:
        raise AuthError("INVALID_PASSWORD", str(error), 422) from None
    principal.password_hash = encoded
    principal.must_change_password = False
    principal.updated_at = now
    revoke_sessions(session, principal_id, now, except_id=session_id)
    session.add(principal)
    session.commit()
