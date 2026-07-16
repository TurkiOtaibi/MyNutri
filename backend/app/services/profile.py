from dataclasses import asdict
from datetime import date
from hashlib import sha256
import json

from sqlmodel import Session, select
from app.core.auth import PrincipalContext
from app.models import Profile, utcnow
from app.schemas import ProfilePreview, ProfileResponse, ProfileUpsert, TargetResponse
from app.services.calc import calculate_targets


def to_target_response(
    profile: Profile | ProfilePreview | ProfileUpsert, calculation_date: date | None = None
) -> TargetResponse:
    result = TargetResponse.model_validate(asdict(calculate_targets(profile, calculation_date)))
    payload = {
        "inputs": {
            "sex": profile.sex.value,
            "birth_date": profile.birth_date.isoformat(),
            "height_cm": float(profile.height_cm),
            "weight_kg": float(profile.weight_kg),
            "activity_level": profile.activity_level.value,
            "goal": profile.goal.value,
            "protein_per_kg": float(profile.protein_per_kg),
            "fat_pct": float(profile.fat_pct),
            "selected_cut_intensity": float(
                getattr(profile, "selected_cut_intensity", getattr(profile, "cut_intensity", 0.2))
            ),
        },
        "result": result.model_dump(mode="json", exclude={"preview_hash"}),
    }
    result.preview_hash = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return result


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
        selected_cut_intensity=float(profile.cut_intensity),
        updated_at=profile.updated_at,
        targets=to_target_response(profile),
    )


def get_profile(session: Session, principal: PrincipalContext) -> Profile | None:
    return session.exec(
        select(Profile).where(Profile.principal_id == principal.principal_id)
    ).first()


def upsert_profile(
    session: Session, principal: PrincipalContext, payload: ProfileUpsert
) -> Profile:
    profile = get_profile(session, principal)
    data = payload.model_dump()
    data["cut_intensity"] = data.pop("selected_cut_intensity")
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


def preview_targets(payload: ProfilePreview, calculation_date: date | None = None) -> TargetResponse:
    return to_target_response(payload, calculation_date)
