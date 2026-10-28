from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.db.session import get_session
from app.models import Principal, PrincipalRole
from app.services.internal_auth import AuthError, admit_session


@dataclass(frozen=True, slots=True)
class PrincipalContext:
    principal_id: UUID
    auth_user_id: UUID | None = None
    role: PrincipalRole = PrincipalRole.user
    email: str | None = None
    display_name: str | None = None
    username: str | None = None
    must_change_password: bool = False
    session_id: UUID | None = None


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
        headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
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
    session: Session = Depends(get_session),
) -> PrincipalContext:
    credential = _credential_from_security(request, credentials)
    try:
        principal, current = admit_session(session, credential, datetime.now(timezone.utc))
    except AuthError as error:
        raise _authentication_error(error.code, error.message_ar) from None
    _enforce_password_change(request, principal)
    return PrincipalContext(
        principal_id=principal.id, auth_user_id=principal.auth_user_id,
        role=principal.role, email=principal.email, display_name=principal.display_name,
        username=principal.username, must_change_password=principal.must_change_password,
        session_id=current.id,
    )


def _enforce_password_change(request: Request, principal: Principal) -> None:
    if principal.must_change_password and not (
        request.method == "POST" and request.url.path in {"/auth/change-password", "/auth/logout"}
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": "PASSWORD_CHANGE_REQUIRED", "message_ar": "يجب تغيير كلمة المرور الأولية للمتابعة."},
            headers={"Cache-Control": "no-store"},
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
