from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import require_single_user
from app.db.session import get_session
from app.schemas import ProfileResponse, ProfileUpsert, TargetResponse
from app.services.profile import get_profile, preview_targets, to_profile_response, upsert_profile

router = APIRouter(prefix="/profile", tags=["profile"], dependencies=[Depends(require_single_user)])


@router.get("", response_model=ProfileResponse)
def read_profile(session: Session = Depends(get_session)) -> ProfileResponse:
    profile = get_profile(session)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return to_profile_response(profile)


@router.put("", response_model=ProfileResponse)
def save_profile(payload: ProfileUpsert, session: Session = Depends(get_session)) -> ProfileResponse:
    profile = upsert_profile(session, payload)
    return to_profile_response(profile)


@router.post("/preview", response_model=TargetResponse)
def preview_profile(payload: ProfileUpsert) -> TargetResponse:
    return preview_targets(payload)
