from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.db.session import get_session
from app.nutrition_rules.calculation import CalculationError
from app.schemas import ProfilePreview, ProfileResponse, ProfileUpsert, TargetResponse
from app.services.profile import get_profile, preview_targets, to_profile_response, upsert_profile
from app.core.calendar import diary_calendar_authority

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def read_profile(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> ProfileResponse:
    profile = get_profile(session, principal)
    if profile is None:
        from app.services.errors import resource_not_found

        raise resource_not_found()
    authority = diary_calendar_authority()
    response = to_profile_response(profile, authority.current_diary_date)
    from app.services.target_plans import pending_plan, resolve_targets

    source = resolve_targets(session, principal, authority.current_diary_date)
    if source.targets is not None:
        response.targets = source.targets
        response.target_provenance = source.target_provenance
        response.effective_plan = source.plan
    response.pending_plan = pending_plan(session, principal)
    return response


@router.put("", response_model=ProfileResponse)
def save_profile(
    payload: ProfileUpsert,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> ProfileResponse:
    authority = diary_calendar_authority()
    return upsert_profile(session, principal, payload, authority.current_diary_date)


@router.post("/preview", response_model=TargetResponse)
def preview_profile(
    payload: ProfilePreview,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> TargetResponse | JSONResponse:
    try:
        authority = diary_calendar_authority()
        effective_date = authority.current_diary_date
        if get_profile(session, principal) is not None:
            effective_date += timedelta(days=1)
        return preview_targets(payload, effective_date)
    except CalculationError as error:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": error.code,
                    "message_ar": error.message_ar,
                    "dimension": error.dimension,
                    "details": {},
                    "request_id": str(uuid4()),
                }
            },
        )
