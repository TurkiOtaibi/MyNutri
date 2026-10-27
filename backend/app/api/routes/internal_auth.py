"""No-cookie internal authentication; validation never echoes credential inputs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictStr
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.db.session import get_session
from app.schemas import AccountResponse
from app.services.internal_auth import AuthError, LOGIN_MESSAGE, change_password, login, logout


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: StrictStr = Field(max_length=32)
    password: SecretStr = Field(max_length=256)


class LoginResponse(BaseModel):
    access_token: str = Field(repr=False)
    token_type: str = "bearer"
    expires_at: datetime
    account: AccountResponse


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr = Field(max_length=256)
    new_password: SecretStr = Field(max_length=256)


class PasswordChangeResponse(BaseModel):
    message_ar: str


class InternalAuthRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request: Request):
            try:
                response = await handler(request)
            except AuthError as error:
                response = JSONResponse(
                    status_code=error.status_code,
                    content={"detail": {"code": error.code, "message_ar": error.message_ar}},
                )
            except RequestValidationError:
                # In particular, JSON parse errors and extra fields may contain secrets.
                response = JSONResponse(
                    status_code=422,
                    content={"detail": {"code": "INVALID_REQUEST", "message_ar": LOGIN_MESSAGE}},
                )
            response.headers["Cache-Control"] = "no-store"
            return response

        return guarded


router = APIRouter(prefix="/auth", tags=["internal-auth"], route_class=InternalAuthRoute)


@router.post("/login", response_model=LoginResponse)
def login_account(payload: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    result = login(
        session, payload.username, payload.password.get_secret_value(), datetime.now(timezone.utc)
    )
    row = result.principal
    return LoginResponse(
        access_token=result.token,
        expires_at=result.expires_at,
        account=AccountResponse(
            principal_id=row.id,
            auth_user_id=row.auth_user_id,
            email=row.email,
            display_name=row.display_name,
            role=row.role,
            status=row.status,
            username=row.username,
            must_change_password=row.must_change_password,
        ),
    )


@router.post("/logout", status_code=204)
def logout_account(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    if principal.session_id is None:
        raise AuthError(
            "INTERNAL_SESSION_REQUIRED", "سجّل الدخول باسم المستخدم لتنفيذ هذا الإجراء.", 403
        )
    logout(session, principal.principal_id, principal.session_id, datetime.now(timezone.utc))
    return Response(status_code=204)


@router.post("/change-password", response_model=PasswordChangeResponse)
def change_account_password(
    payload: PasswordChangeRequest,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> PasswordChangeResponse:
    if principal.session_id is None:
        raise AuthError(
            "INTERNAL_SESSION_REQUIRED", "سجّل الدخول باسم المستخدم لتنفيذ هذا الإجراء.", 403
        )
    change_password(
        session,
        principal.principal_id,
        principal.session_id,
        payload.current_password.get_secret_value(),
        payload.new_password.get_secret_value(),
        datetime.now(timezone.utc),
    )
    return PasswordChangeResponse(message_ar="تم تغيير كلمة المرور.")
