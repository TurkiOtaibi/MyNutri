from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.db.session import get_session
from app.schemas import ProfileResponse, ProfileUpsert, TargetResponse
from app.services.profile import get_profile, preview_targets, to_profile_response, upsert_profile

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
    return to_profile_response(profile)


@router.put("", response_model=ProfileResponse)
def save_profile(
    payload: ProfileUpsert,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> ProfileResponse:
    profile = upsert_profile(session, principal, payload)
    return to_profile_response(profile)


@router.post("/preview", response_model=TargetResponse)
def preview_profile(
    payload: ProfileUpsert,
    principal: PrincipalContext = Depends(get_principal_context),
) -> TargetResponse:
    del principal
    return preview_targets(payload)
