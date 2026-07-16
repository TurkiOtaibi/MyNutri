from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.schemas import (
    TargetPlanActivationRequest,
    TargetPlanActivationResponse,
    TargetPlanHistoryResponse,
    TargetPlanReplacementRequest,
    TargetPlanSummary,
    TargetSourceResponse,
)
from app.services.target_plans import (
    TargetPlanError,
    activate_plan,
    pending_plan,
    plan_history,
    resolve_targets,
)

router = APIRouter(prefix="/target-plans", tags=["target-plans"])


def _error(error: TargetPlanError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message_ar": error.message_ar, "details": {}, "request_id": str(uuid4())}},
    )


@router.post("/activate", response_model=TargetPlanActivationResponse, status_code=201)
def activate(
    payload: TargetPlanActivationRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        response, replayed = activate_plan(session, principal, payload, idempotency_key)
        headers = {"Idempotent-Replayed": "true"} if replayed else None
        return JSONResponse(status_code=201, content=response.model_dump(mode="json"), headers=headers)
    except TargetPlanError as error:
        return _error(error)


@router.post("/pending/replace", response_model=TargetPlanActivationResponse, status_code=201)
def replace(
    payload: TargetPlanReplacementRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        response, replayed = activate_plan(
            session, principal, payload, idempotency_key, replace_pending=True
        )
        headers = {"Idempotent-Replayed": "true"} if replayed else None
        return JSONResponse(status_code=201, content=response.model_dump(mode="json"), headers=headers)
    except TargetPlanError as error:
        return _error(error)


@router.get("/current", response_model=TargetSourceResponse)
def current(
    requested_date: date | None = Query(default=None, alias="date"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    return resolve_targets(session, principal, requested_date or current_diary_date())


@router.get("/pending", response_model=TargetPlanSummary | None)
def pending(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    return pending_plan(session, principal)


@router.get("", response_model=TargetPlanHistoryResponse)
def history(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        return plan_history(session, principal, limit, cursor)
    except TargetPlanError as error:
        return _error(error)
