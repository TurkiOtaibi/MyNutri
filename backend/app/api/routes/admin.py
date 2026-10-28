from datetime import date
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlmodel import Session, select

from app.api.routes.labs import ERROR_RESPONSES, LabsRoute
from app.labs.catalog import get_catalog
from app.labs.types import Catalog
from app.services import labs as labs_service
from app.core.auth import PrincipalContext, require_admin
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.models import DiaryEntry, Principal, PrincipalStatus, Profile
from app.schemas import (
    LabOverviewResponse,
    LabTestDetailResponse,
    AdminUserDetail,
    DaySummary,
    AdminDiaryPage,
    AdminUserListResponse,
    AdminUserSummary,
)
from app.nutrition_rules.calculation import age_on
from app.services.aggregation import admin_day_summaries
from app.services.diary import AdminDiaryCursorError, admin_diary_page
from app.services.errors import resource_not_found
from app.services.profile import to_profile_response
from app.services.target_plans import TargetPlanError, plan_history, resolve_targets

router = APIRouter(prefix="/admin", tags=["admin"])


def _selected_context(principal: Principal) -> PrincipalContext:
    return PrincipalContext(
        principal_id=principal.id,
        auth_user_id=principal.auth_user_id,
        role=principal.role,
        email=principal.email,
        display_name=principal.display_name,
    )


def _get_principal(session: Session, principal_id: UUID) -> Principal:
    principal = session.get(Principal, principal_id, populate_existing=True)
    if principal is None or principal.status not in {
        PrincipalStatus.active, PrincipalStatus.disabled,
    }:
        raise resource_not_found()
    return principal


def _summary_statement(conditions: list, page: int, page_size: int):
    principals = (
        select(Principal.id.label("principal_id"), Principal.created_at.label("created_at"))
        .where(*conditions)
        .order_by(Principal.created_at.desc(), Principal.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .cte("page_principals")
    )
    activity = select(
        DiaryEntry.principal_id.label("principal_id"),
        func.max(DiaryEntry.created_at).label("last_activity_at"),
    ).join(principals, DiaryEntry.principal_id == principals.c.principal_id).group_by(
        DiaryEntry.principal_id
    ).subquery()
    return (
        select(Principal, Profile.goal, Profile.principal_id, activity.c.last_activity_at)
        .join(principals, Principal.id == principals.c.principal_id)
        .outerjoin(Profile, Profile.principal_id == Principal.id)
        .outerjoin(activity, activity.c.principal_id == Principal.id)
        .order_by(principals.c.created_at.desc(), Principal.id.desc())
    )


def _summary_from_row(row) -> AdminUserSummary:
    principal, goal, profile_principal_id, last_activity = row
    return AdminUserSummary(
        principal_id=principal.id,
        email=principal.email,
        username=principal.username,
        last_login_at=principal.last_login_at,
        is_locked=principal.role == "user" and principal.password_hash is not None and principal.locked_at is not None,
        display_name=principal.display_name,
        status=principal.status,
        role=principal.role,
        created_at=principal.created_at,
        profile_complete=profile_principal_id is not None,
        current_goal=goal,
        last_activity_at=last_activity,
    )


def _summary(session: Session, principal: Principal) -> AdminUserSummary:
    last_activity = (
        select(func.max(DiaryEntry.created_at))
        .where(DiaryEntry.principal_id == Principal.id)
        .scalar_subquery()
    )
    row = session.exec(
        select(Principal, Profile.goal, Profile.principal_id, last_activity)
        .outerjoin(Profile, Profile.principal_id == Principal.id)
        .where(Principal.id == principal.id)
    ).one()
    return _summary_from_row(row)


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AdminUserListResponse:
    # Lifecycle-incomplete accounts belong to the separate account-management
    # surface, not the existing read-only user monitoring list.
    conditions = [Principal.status.in_([PrincipalStatus.active, PrincipalStatus.disabled])]
    if search and search.strip():
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append(
            or_(Principal.username.ilike(pattern, escape="\\"),
                Principal.display_name.ilike(pattern, escape="\\"),
                and_(Principal.username.is_(None), Principal.email.ilike(pattern, escape="\\")))
        )
    count = select(func.count()).select_from(Principal)
    statement = _summary_statement(conditions, page, page_size)
    if conditions:
        count = count.where(*conditions)
    total = int(session.exec(count).one())
    rows = session.exec(
        statement
    ).all()
    return AdminUserListResponse(
        items=[_summary_from_row(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.get("/users/{principal_id}", response_model=AdminUserDetail)
def user_detail(
    principal_id: UUID,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    plan_cursor: str | None = Query(default=None),
    plan_limit: int = Query(default=20, ge=1, le=100),
) -> AdminUserDetail:
    principal = _get_principal(session, principal_id)
    selected = _selected_context(principal)
    profile = session.exec(select(Profile).where(Profile.principal_id == principal.id)).first()
    today = current_diary_date()
    target = resolve_targets(session, selected, today)
    try:
        history = plan_history(session, selected, plan_limit, plan_cursor)
    except TargetPlanError as error:
        raise HTTPException(status_code=error.status_code, detail={
            "code": error.code, "message_ar": error.message_ar,
        }) from error
    return AdminUserDetail(
        age=age_on(profile.birth_date, today=today) if profile else None,
        account=_summary(session, principal),
        profile=(
            to_profile_response(profile, resolved_targets=target.targets)
            if profile
            else None
        ),
        current_target=target,
        plan_history=history,
    )


@router.get("/users/{principal_id}/diary", response_model=AdminDiaryPage)
def user_diary(
    principal_id: UUID,
    entry_date: date | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> AdminDiaryPage:
    selected = _selected_context(_get_principal(session, principal_id))
    try:
        return admin_diary_page(session, selected, limit, cursor, entry_date)
    except AdminDiaryCursorError as error:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CURSOR"}) from error


@router.get("/users/{principal_id}/diary/summaries", response_model=list[DaySummary])
def user_diary_summaries(
    principal_id: UUID,
    dates: list[date] = Query(min_length=1, max_length=100),
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[DaySummary]:
    selected = _selected_context(_get_principal(session, principal_id))
    return admin_day_summaries(session, selected, dates)


# A separate route class keeps the privacy boundary scoped to Labs monitoring.
labs_router = APIRouter(route_class=LabsRoute, responses=ERROR_RESPONSES)


@labs_router.get("/users/{principal_id}/labs", response_model=LabOverviewResponse)
def user_labs(
    principal_id: UUID,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    catalog: Catalog = Depends(get_catalog),
) -> LabOverviewResponse:
    _get_principal(session, principal_id)
    return labs_service.read_labs(session, principal_id, True, catalog)


@labs_router.get("/users/{principal_id}/labs/tests/{test_key}", response_model=LabTestDetailResponse)
def user_lab_test(
    principal_id: UUID,
    test_key: str,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
    catalog: Catalog = Depends(get_catalog),
) -> LabTestDetailResponse:
    _get_principal(session, principal_id)
    return labs_service.read_lab_test(session, principal_id, test_key, True, catalog)


router.include_router(labs_router)
