"""Admin account mutations, separate from read-only selected-user monitoring."""

from datetime import datetime, timezone
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import and_, func, or_
from sqlmodel import Session, select

from app.core.auth import PrincipalContext, require_admin
from app.core.credentials import USERNAME_MESSAGE
from app.db.session import get_session
from app.models import Principal, PrincipalStatus, Profile
from app.schemas import (
    AdminAccountCounts,
    AdminInternalAccountCreate,
    AdminAccountDelete,
    AdminAccountEdit,
    AdminAccountEnable,
    AdminAccountList,
    AdminAccountPasswordReset,
    AdminAccountSummary,
    AdminProfileSexCorrection,
)
from app.services.admin_profile import correct_profile_sex
from app.services.admin_lifecycle import (
    LifecycleError,
    create_internal_account,
    delete_account,
    edit_display_name,
    reset_account_password,
    set_account_enabled,
    _admin,
    _target,
)


class AccountManagementRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request: Request):
            try:
                response = await handler(request)
            except LifecycleError as error:
                response = JSONResponse(
                    status_code=error.status_code,
                    content={"error": {"code": error.code, "message_ar": error.message_ar}},
                )
            except RequestValidationError as error:
                if any(item.get("loc", ())[-1:] == ("username",) and item.get("type") in {"string_too_long", "string_too_short"} for item in error.errors()):
                    return JSONResponse(status_code=422, headers={"Cache-Control": "no-store"}, content={"error": {"code": "INVALID_USERNAME", "message_ar": USERNAME_MESSAGE}})
                response = JSONResponse(
                    status_code=422,
                    content={"error": {"code": "INVALID_REQUEST", "details": [
                        {"loc": list(item.get("loc", ())), "type": item.get("type", "value_error")}
                        for item in error.errors()
                    ]}},
                )
            response.headers["Cache-Control"] = "no-store"
            return response

        return guarded


router = APIRouter(prefix="/admin/accounts", tags=["admin-accounts"], route_class=AccountManagementRoute)
def _summary(row: Principal, profile_complete: bool | None = None) -> AdminAccountSummary:
    if profile_complete is None:
        session = Session.object_session(row)
        assert session is not None
        profile_complete = session.scalar(
            select(Profile.id).where(Profile.principal_id == row.id)
        ) is not None
    return AdminAccountSummary(
        principal_id=row.id,
        email=row.email,
        username=row.username,
        last_login_at=row.last_login_at,
        is_locked=row.role == "user" and row.password_hash is not None and row.locked_at is not None,
        display_name=row.display_name,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        disabled_at=row.disabled_at,
        profile_complete=profile_complete,
    )


def _normal_target(
    principal_id: UUID,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> Principal:
    _admin(session, admin.principal_id)
    return _target(session, admin.principal_id, principal_id)


@router.get("", response_model=AdminAccountList)
def list_accounts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=320),
    status: PrincipalStatus | Literal["locked"] | None = None,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AdminAccountList:
    conditions = [Principal.role == "user", Principal.status != PrincipalStatus.deleted]
    if status == "locked":
        conditions.extend([Principal.password_hash.is_not(None), Principal.locked_at.is_not(None)])
    elif status is not None:
        conditions.append(Principal.status == status)
    if search and search.strip():
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append(
            or_(Principal.username.ilike(pattern, escape="\\"),
                Principal.display_name.ilike(pattern, escape="\\"),
                and_(Principal.username.is_(None), Principal.email.ilike(pattern, escape="\\")))
        )
    statement = select(Principal, Profile.id).outerjoin(
        Profile, Profile.principal_id == Principal.id
    ).where(*conditions)
    total = int(session.exec(
        select(func.count()).select_from(Principal).where(*conditions)
    ).one())
    rows = session.exec(
        statement.order_by(Principal.created_at.desc(), Principal.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    counts = dict(session.exec(
        select(Principal.status, func.count()).where(
            Principal.role == "user", Principal.status != PrincipalStatus.deleted
        ).group_by(Principal.status)
    ).all())
    self_row = session.get(Principal, _admin.principal_id) if page == 1 and not (search and search.strip()) and status is None else None
    return AdminAccountList(
        self=_summary(self_row) if self_row is not None else None,
        counts=AdminAccountCounts(**counts),
        items=[_summary(row, profile_id is not None) for row, profile_id in rows],
        total=total, page=page, page_size=page_size
    )


@router.put("/{principal_id}/profile/sex", status_code=204)
def correct_sex(
    principal_id: UUID,
    payload: AdminProfileSexCorrection,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> None:
    correct_profile_sex(session, admin.principal_id, principal_id, payload.sex)


@router.post("", response_model=AdminAccountSummary, status_code=201)
def create(
    payload: AdminInternalAccountCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AdminAccountSummary:
    return _summary(create_internal_account(
        session, admin.principal_id, payload.username, payload.display_name,
        payload.initial_password, idempotency_key, datetime.now(timezone.utc),
    ))


@router.patch("/{principal_id}", response_model=AdminAccountSummary)
def edit(
    principal_id: UUID,
    payload: AdminAccountEdit,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AdminAccountSummary:
    return _summary(edit_display_name(
        session, admin.principal_id, principal_id, payload.display_name, datetime.now(timezone.utc)
    ))


@router.put("/{principal_id}/password", status_code=204)
def reset_password(
    principal_id: UUID,
    payload: AdminAccountPasswordReset,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    _target_row: Principal = Depends(_normal_target),
) -> None:
    reset_account_password(
        session, admin.principal_id, principal_id, payload.new_password,
        datetime.now(timezone.utc),
    )


@router.put("/{principal_id}/status", response_model=AdminAccountSummary)
def change_status(
    principal_id: UUID,
    payload: AdminAccountEnable,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AdminAccountSummary:
    return _summary(set_account_enabled(
        session, admin.principal_id, principal_id, payload.enabled, datetime.now(timezone.utc)
    ))


@router.delete("/{principal_id}", response_model=AdminAccountSummary)
def remove(
    principal_id: UUID,
    payload: AdminAccountDelete = Body(...),
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    _target_row: Principal = Depends(_normal_target),
) -> AdminAccountSummary:
    result = delete_account(
        session, admin.principal_id, principal_id, datetime.now(timezone.utc),
        confirmation_email=payload.confirm_email,
        confirmation_username=payload.confirm_username,
        require_confirmation=True,
    )
    return _summary(result)
