from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session
from sqlmodel import select

from app.core.config import Settings, get_settings
from app.core.jwks import RotationSafeJwksClient
from app.db.session import get_session
from app.models import Principal, PrincipalRole, PrincipalStatus


@dataclass(frozen=True, slots=True)
class PrincipalContext:
    principal_id: UUID
    auth_user_id: UUID | None = None
    role: PrincipalRole = PrincipalRole.user
    email: str | None = None
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class AuthClaims:
    auth_user_id: UUID
    email: str | None
    display_name: str | None


class SupabaseTokenVerifier:
    def __init__(self, settings: Settings) -> None:
        if not settings.normalized_supabase_url:
            raise RuntimeError("SUPABASE_URL is required for authentication.")
        self.issuer = settings.expected_supabase_issuer
        self.audience = settings.supabase_jwt_audience
        self.jwks = RotationSafeJwksClient(
            settings.effective_supabase_jwks_url,
            timeout_seconds=settings.supabase_jwks_timeout_seconds,
            cache_lifespan_seconds=settings.supabase_jwks_cache_lifespan_seconds,
            refresh_cooldown_seconds=settings.supabase_jwks_refresh_cooldown_seconds,
            max_keys=settings.supabase_jwks_max_keys,
            kid_max_length=settings.supabase_jwt_kid_max_length,
        )

    def verify(self, token: str) -> AuthClaims:
        signing_key = self.jwks.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        auth_user_id = UUID(str(payload["sub"]))
        email_value = payload.get("email")
        email = str(email_value).strip().lower()[:320] if email_value else None
        metadata = payload.get("user_metadata")
        display_name = None
        if isinstance(metadata, dict):
            candidate = next(
                (
                    metadata.get(key)
                    for key in ("display_name", "full_name", "name")
                    if metadata.get(key)
                ),
                None,
            )
            if candidate:
                display_name = " ".join(str(candidate).strip().split())[:120] or None
        return AuthClaims(auth_user_id, email, display_name)


@lru_cache(maxsize=8)
def _cached_verifier(
    url: str,
    jwks_url: str,
    audience: str,
    timeout_seconds: int,
    cache_lifespan_seconds: int,
    refresh_cooldown_seconds: int,
    max_keys: int,
    kid_max_length: int,
) -> SupabaseTokenVerifier:
    return SupabaseTokenVerifier(
        Settings(
            environment="test",
            supabase_url=url,
            supabase_jwks_url=jwks_url,
            supabase_jwt_audience=audience,
            supabase_jwks_timeout_seconds=timeout_seconds,
            supabase_jwks_cache_lifespan_seconds=cache_lifespan_seconds,
            supabase_jwks_refresh_cooldown_seconds=refresh_cooldown_seconds,
            supabase_jwks_max_keys=max_keys,
            supabase_jwt_kid_max_length=kid_max_length,
        )
    )


def get_token_verifier(settings: Settings = Depends(get_settings)) -> SupabaseTokenVerifier:
    return _cached_verifier(
        settings.normalized_supabase_url,
        settings.effective_supabase_jwks_url,
        settings.supabase_jwt_audience,
        settings.supabase_jwks_timeout_seconds,
        settings.supabase_jwks_cache_lifespan_seconds,
        settings.supabase_jwks_refresh_cooldown_seconds,
        settings.supabase_jwks_max_keys,
        settings.supabase_jwt_kid_max_length,
    )


bearer_auth = HTTPBearer(
    auto_error=False,
    bearerFormat="token",
    scheme_name="BearerAuth",
    description="Enter the bearer token only. Swagger UI adds the Bearer scheme.",
)


def _authentication_error(code: str, message_ar: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message_ar": message_ar},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _credential_from_security(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None:
        if request.headers.get("Authorization") is not None:
            raise _authentication_error("INVALID_CREDENTIAL", "بيانات الدخول غير صالحة.")
        raise _authentication_error("AUTHENTICATION_REQUIRED", "يلزم تسجيل الدخول للمتابعة.")
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _authentication_error("INVALID_CREDENTIAL", "بيانات الدخول غير صالحة.")
    return credentials.credentials


def get_principal_context(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_auth),
    ],
    verifier: SupabaseTokenVerifier = Depends(get_token_verifier),
    session: Session = Depends(get_session),
) -> PrincipalContext:
    credential = _credential_from_security(request, credentials)
    try:
        claims = verifier.verify(credential)
    except (PyJWTError, ValueError, RuntimeError):
        raise _authentication_error("INVALID_CREDENTIAL", "بيانات الدخول غير صالحة.")
    principal = session.exec(
        select(Principal).where(Principal.auth_user_id == claims.auth_user_id)
    ).one_or_none()
    if principal is None:
        principal = Principal(
            auth_user_id=claims.auth_user_id,
            email=claims.email,
            display_name=claims.display_name,
            role=PrincipalRole.user,
        )
        session.add(principal)
        try:
            session.commit()
            session.refresh(principal)
        except IntegrityError:
            session.rollback()
            principal = session.exec(
                select(Principal).where(Principal.auth_user_id == claims.auth_user_id)
            ).one_or_none()
    if principal is None or principal.status != PrincipalStatus.active:
        raise _authentication_error("INVALID_CREDENTIAL", "بيانات الدخول غير صالحة.")
    return PrincipalContext(
        principal_id=principal.id,
        auth_user_id=claims.auth_user_id,
        role=principal.role,
        email=principal.email,
        display_name=principal.display_name,
    )


def require_admin(
    principal: PrincipalContext = Depends(get_principal_context),
) -> PrincipalContext:
    if principal.role != PrincipalRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message_ar": "ليس لديك صلاحية لتنفيذ هذا الإجراء."},
        )
    return principal
