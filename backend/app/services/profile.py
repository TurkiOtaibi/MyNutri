from sqlmodel import Session, select
from uuid import UUID

from app.core.auth import PrincipalContext
from app.models import Profile, utcnow
from app.schemas import ProfileResponse, ProfileUpsert, TargetResponse
from app.services.calc import calculate_targets
from app.services.nutrients import nutrient_target_payloads


def to_target_response(profile: Profile) -> TargetResponse:
    return TargetResponse.model_validate({**calculate_targets(profile).__dict__, "additional_targets": nutrient_target_payloads()})


def to_profile_response(profile: Profile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        sex=profile.sex,
        birth_date=profile.birth_date,
        height_cm=float(profile.height_cm),
        weight_kg=float(profile.weight_kg),
        activity_level=profile.activity_level,
        goal=profile.goal,
        protein_per_kg=float(profile.protein_per_kg),
        fat_pct=float(profile.fat_pct),
        updated_at=profile.updated_at,
        targets=to_target_response(profile),
    )


def get_profile(session: Session, principal: PrincipalContext) -> Profile | None:
    return session.exec(select(Profile).where(Profile.principal_id == principal.principal_id)).first()


def upsert_profile(session: Session, principal: PrincipalContext, payload: ProfileUpsert) -> Profile:
    profile = get_profile(session, principal)
    data = payload.model_dump()
    if profile is None:
        profile = Profile(principal_id=principal.principal_id, **data)
    else:
        for key, value in data.items():
            setattr(profile, key, value)
        profile.updated_at = utcnow()

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def preview_targets(payload: ProfileUpsert) -> TargetResponse:
    profile = Profile(principal_id=UUID(int=0), **payload.model_dump())
    return to_target_response(profile)
