"""Admin account mutations, separate from read-only selected-user monitoring."""

import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import func, or_, text
from sqlmodel import Session, select

from app.core.auth import PrincipalContext, require_admin
from app.core.config import Settings, get_settings
from app.db.session import engine, get_session
from app.models import Principal, PrincipalStatus
from app.schemas import (
    AdminAccountCreate,
    AdminAccountDelete,
    AdminAccountEdit,
    AdminAccountEnable,
    AdminAccountList,
    AdminAccountPasswordReset,
    AdminAccountRetryCreate,
    AdminAccountSummary,
)
from app.services.admin_auth import AdminAuthError, AdminAuthGateway, get_admin_auth_gateway
from app.services.admin_lifecycle import (
    LifecycleError,
    create_account,
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
            except AdminAuthError as error:
                if error.kind == "duplicate_email":
                    code, message, status = "DUPLICATE_EMAIL", "هذا البريد الإلكتروني مستخدم بالفعل.", 409
                elif error.kind == "password_rejected":
                    code, message, status = "PASSWORD_REJECTED", "كلمة المرور غير مقبولة. اختر كلمة مرور أقوى وحاول مرة أخرى.", 422
                elif request.url.path.endswith("/password"):
                    code, message, status = "PASSWORD_RESET_FAILED", "تعذر إعادة تعيين كلمة المرور. حاول مرة أخرى.", 503
                elif request.method == "DELETE" or request.url.path.endswith("/retry-delete"):
                    code, message, status = "DELETION_INCOMPLETE", "تعذر إكمال حذف المستخدم. حسابه معطّل ويمكنك إعادة المحاولة.", 503
                else:
                    code, message, status = "CREATION_INCOMPLETE", "تعذر إكمال إنشاء المستخدم. أعد المحاولة.", 503
                response = JSONResponse(
                    status_code=status, content={"error": {"code": code, "message_ar": message}}
                )
            except RequestValidationError as error:
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
logger = logging.getLogger(__name__)


class _RecentReconciliationThrottle:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._last_success: datetime | None = None

    def begin(self, now: datetime) -> bool:
        with self._lock:
            if self._running or (
                self._last_success is not None
                and timedelta(0) <= now - self._last_success < timedelta(minutes=5)
            ):
                return False
            self._running = True
            return True

    def finish(self, now: datetime, *, succeeded: bool) -> None:
        with self._lock:
            if succeeded:
                self._last_success = now
            self._running = False


_list_reconciliation_throttle = _RecentReconciliationThrottle()
_LIST_RECONCILIATION_LOCK_KEY = 0x4D794E7574726941


def _summary(row: Principal) -> AdminAccountSummary:
    return AdminAccountSummary(
        principal_id=row.id,
        email=row.email,
        display_name=row.display_name,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _normal_target(
    principal_id: UUID,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> Principal:
    _admin(session, admin.principal_id)
    return _target(session, admin.principal_id, principal_id)


def _background_reconcile_recent(now: datetime, list_load: bool = False) -> None:
    # A new session and credential scope keep slow Auth calls off the page read.
    from app.services.admin_lifecycle import reconcile_recent_tombstones

    if list_load and not _list_reconciliation_throttle.begin(now):
        return
    succeeded = False
    try:
        gateway = get_admin_auth_gateway(get_settings())
        if list_load and engine.dialect.name == "postgresql":
            with engine.connect() as lock_connection:
                locked = bool(lock_connection.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": _LIST_RECONCILIATION_LOCK_KEY},
                ).scalar_one())
                if not locked:
                    return
                try:
                    with Session(engine) as session:
                        outcome = reconcile_recent_tombstones(session, gateway, now, limit=100)
                    succeeded = outcome["failed"] == 0
                finally:
                    lock_connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"),
                        {"key": _LIST_RECONCILIATION_LOCK_KEY},
                    )
        else:
            with Session(engine) as session:
                outcome = reconcile_recent_tombstones(session, gateway, now, limit=100)
            succeeded = outcome["failed"] == 0
    except AdminAuthError as error:
        logger.warning("retired identity reconciliation failed: type=%s count=1", error.kind)
    except Exception:
        logger.warning("retired identity reconciliation failed: type=unexpected count=1")
    finally:
        if list_load:
            _list_reconciliation_throttle.finish(datetime.now(timezone.utc), succeeded=succeeded)


@router.get("", response_model=AdminAccountList)
def list_accounts(
    background_tasks: BackgroundTasks,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=320),
    status: PrincipalStatus | None = None,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AdminAccountList:
    conditions = [Principal.role == "user", Principal.status != PrincipalStatus.deleted]
    if status is not None:
        conditions.append(Principal.status == status)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(Principal.email.ilike(pattern), Principal.display_name.ilike(pattern))
        )
    statement = select(Principal).where(*conditions)
    total = int(session.exec(
        select(func.count()).select_from(Principal).where(*conditions)
    ).one())
    rows = session.exec(
        statement.order_by(Principal.created_at.desc(), Principal.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    background_tasks.add_task(_background_reconcile_recent, datetime.now(timezone.utc), True)
    return AdminAccountList(
        items=[_summary(row) for row in rows], total=total, page=page, page_size=page_size
    )


@router.post("", response_model=AdminAccountSummary, status_code=201)
def create(
    payload: AdminAccountCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    gateway: AdminAuthGateway = Depends(get_admin_auth_gateway),
    settings: Settings = Depends(get_settings),
) -> AdminAccountSummary:
    return _summary(create_account(
        session, admin.principal_id, payload.email, payload.display_name,
        payload.initial_password, idempotency_key, gateway,
        datetime.now(timezone.utc), settings.supabase_admin_http_timeout_seconds,
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
    gateway: AdminAuthGateway = Depends(get_admin_auth_gateway),
) -> None:
    reset_account_password(
        session, admin.principal_id, principal_id, payload.new_password,
        gateway, datetime.now(timezone.utc),
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
    background_tasks: BackgroundTasks,
    payload: AdminAccountDelete = Body(...),
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    _target_row: Principal = Depends(_normal_target),
    gateway: AdminAuthGateway = Depends(get_admin_auth_gateway),
    settings: Settings = Depends(get_settings),
) -> AdminAccountSummary:
    result = delete_account(
        session, admin.principal_id, principal_id, gateway,
        datetime.now(timezone.utc), settings.supabase_admin_http_timeout_seconds,
        confirmation_email=payload.confirm_email,
    )
    background_tasks.add_task(_background_reconcile_recent, datetime.now(timezone.utc))
    return _summary(result)


@router.post("/{principal_id}/retry-create", response_model=AdminAccountSummary)
def retry_create(
    principal_id: UUID,
    payload: AdminAccountRetryCreate,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    target: Principal = Depends(_normal_target),
    gateway: AdminAuthGateway = Depends(get_admin_auth_gateway),
    settings: Settings = Depends(get_settings),
) -> AdminAccountSummary:
    row = target
    if row.status != PrincipalStatus.provisioning:
        raise LifecycleError(409, "CREATION_INCOMPLETE", "تعذر إكمال إنشاء المستخدم. أعد المحاولة.")
    assert row.email is not None and row.display_name is not None
    assert row.creation_idempotency_key is not None
    return _summary(create_account(
        session, admin.principal_id, row.email, row.display_name,
        payload.initial_password, row.creation_idempotency_key, gateway,
        datetime.now(timezone.utc), settings.supabase_admin_http_timeout_seconds,
    ))


@router.post("/{principal_id}/retry-delete", response_model=AdminAccountSummary)
def retry_delete(
    principal_id: UUID,
    background_tasks: BackgroundTasks,
    admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    target: Principal = Depends(_normal_target),
    gateway: AdminAuthGateway = Depends(get_admin_auth_gateway),
    settings: Settings = Depends(get_settings),
) -> AdminAccountSummary:
    row = target
    if row.status != PrincipalStatus.deleting:
        raise LifecycleError(404, "RESOURCE_NOT_FOUND", "المورد غير موجود.")
    result = delete_account(
        session, admin.principal_id, principal_id, gateway,
        datetime.now(timezone.utc), settings.supabase_admin_http_timeout_seconds,
    )
    background_tasks.add_task(_background_reconcile_recent, datetime.now(timezone.utc))
    return _summary(result)
