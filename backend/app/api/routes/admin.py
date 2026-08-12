from datetime import date
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.auth import PrincipalContext, require_admin
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.models import DiaryEntry, Principal, Profile
from app.schemas import (
    AdminUserDetail,
    AdminDiaryPage,
    AdminUserListResponse,
    AdminUserSummary,
    TargetPlanHistoryResponse,
    WeekSummary,
)
from app.services.aggregation import weekly_summary_read_only
from app.services.diary import AdminDiaryCursorError, admin_diary_page
from app.services.errors import resource_not_found
from app.services.profile import to_profile_response
from app.services.target_plans import pending_plan, plan_history, project_targets

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
    principal = session.get(Principal, principal_id)
    if principal is None:
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
    conditions = []
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(Principal.email.ilike(pattern), Principal.display_name.ilike(pattern))
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
) -> AdminUserDetail:
    principal = _get_principal(session, principal_id)
    selected = _selected_context(principal)
    profile = session.exec(select(Profile).where(Profile.principal_id == principal.id)).first()
    return AdminUserDetail(
        account=_summary(session, principal),
        profile=to_profile_response(profile) if profile else None,
        current_target=project_targets(session, selected, current_diary_date()),
        pending_plan=pending_plan(session, selected),
        plan_history=plan_history(session, selected, 100, None),
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


@router.get("/users/{principal_id}/diary/week", response_model=WeekSummary)
def user_week(
    principal_id: UUID,
    start: date,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> WeekSummary:
    selected = _selected_context(_get_principal(session, principal_id))
    return weekly_summary_read_only(session, selected, start)


@router.get("/users/{principal_id}/target-plans", response_model=TargetPlanHistoryResponse)
def user_target_plans(
    principal_id: UUID,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> TargetPlanHistoryResponse:
    selected = _selected_context(_get_principal(session, principal_id))
    return plan_history(session, selected, 100, None)
