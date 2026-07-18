from datetime import date
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.auth import PrincipalContext, require_admin
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.models import DiaryEntry, Principal, Profile
from app.schemas import (
    AdminUserDetail,
    AdminUserListResponse,
    AdminUserSummary,
    DiaryEntryResponse,
    TargetPlanHistoryResponse,
    WeekSummary,
)
from app.services.aggregation import weekly_summary
from app.services.diary import list_entries, to_entry_response
from app.services.errors import resource_not_found
from app.services.profile import to_profile_response
from app.services.target_plans import pending_plan, plan_history, resolve_targets

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


def _summary(session: Session, principal: Principal) -> AdminUserSummary:
    profile = session.exec(select(Profile).where(Profile.principal_id == principal.id)).first()
    last_activity = session.exec(
        select(func.max(DiaryEntry.created_at)).where(DiaryEntry.principal_id == principal.id)
    ).one()
    return AdminUserSummary(
        principal_id=principal.id,
        email=principal.email,
        display_name=principal.display_name,
        status=principal.status,
        role=principal.role,
        created_at=principal.created_at,
        profile_complete=profile is not None,
        current_goal=profile.goal if profile else None,
        last_activity_at=last_activity,
    )


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
    statement = select(Principal)
    if conditions:
        count = count.where(*conditions)
        statement = statement.where(*conditions)
    total = int(session.exec(count).one())
    principals = session.exec(
        statement.order_by(Principal.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AdminUserListResponse(
        items=[_summary(session, principal) for principal in principals],
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
        current_target=resolve_targets(session, selected, current_diary_date()),
        pending_plan=pending_plan(session, selected),
        plan_history=plan_history(session, selected, 100, None),
    )


@router.get("/users/{principal_id}/diary", response_model=list[DiaryEntryResponse])
def user_diary(
    principal_id: UUID,
    entry_date: date | None = None,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[DiaryEntryResponse]:
    selected = _selected_context(_get_principal(session, principal_id))
    return [to_entry_response(entry) for entry in list_entries(session, selected, entry_date)]


@router.get("/users/{principal_id}/diary/week", response_model=WeekSummary)
def user_week(
    principal_id: UUID,
    start: date,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> WeekSummary:
    selected = _selected_context(_get_principal(session, principal_id))
    return weekly_summary(session, selected, start)


@router.get("/users/{principal_id}/target-plans", response_model=TargetPlanHistoryResponse)
def user_target_plans(
    principal_id: UUID,
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
) -> TargetPlanHistoryResponse:
    selected = _selected_context(_get_principal(session, principal_id))
    return plan_history(session, selected, 100, None)
