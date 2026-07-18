import secrets
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.models import Principal, PrincipalStatus


@dataclass(frozen=True, slots=True)
class PrincipalContext:
    principal_id: UUID


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
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> PrincipalContext:
    credential = _credential_from_security(request, credentials)
    principal_id = next(
        (
            candidate_id
            for candidate, candidate_id in settings.credential_map().items()
            if secrets.compare_digest(credential, candidate)
        ),
        None,
    )
    if principal_id is None:
        raise _authentication_error("INVALID_CREDENTIAL", "بيانات الدخول غير صالحة.")

    principal = session.get(Principal, principal_id)
    if principal is None or principal.status != PrincipalStatus.active:
        raise _authentication_error("INVALID_CREDENTIAL", "بيانات الدخول غير صالحة.")
    return PrincipalContext(principal_id=principal.id)


# Compatibility alias for imports outside the route layer. It now establishes identity.
require_single_user = get_principal_context
