from dataclasses import asdict
from datetime import date
from hashlib import sha256
import json

from fastapi.exceptions import RequestValidationError
from sqlmodel import Session, select
from app.core.auth import PrincipalContext
from app.core.calendar import current_diary_date
from app.models import Profile, utcnow
from app.schemas import (
    ProfileDomainValidationError,
    ProfilePreview,
    ProfileResponse,
    ProfileUpsert,
    TargetResponse,
    validate_profile_domain,
)
from app.services.calc import calculate_targets


def _validate_profile_domain(
    profile: ProfileUpsert, calculation_date: date
) -> None:
    try:
        validate_profile_domain(profile, calculation_date)
    except ProfileDomainValidationError as error:
        value = error.value.isoformat() if isinstance(error.value, date) else error.value
        raise RequestValidationError(
            [
                {
                    "type": error.code,
                    "loc": ("body", error.field),
                    "msg": error.message,
                    "input": value,
                }
            ]
        ) from error


def to_target_response(
    profile: Profile | ProfilePreview | ProfileUpsert, calculation_date: date | None = None
) -> TargetResponse:
    effective_date = calculation_date or current_diary_date()
    validation_payload = (
        profile
        if isinstance(profile, ProfileUpsert)
        else ProfileUpsert(
            sex=profile.sex,
            birth_date=profile.birth_date,
            height_cm=float(profile.height_cm),
            weight_kg=float(profile.weight_kg),
            activity_level=profile.activity_level,
            goal=profile.goal,
            protein_per_kg=float(profile.protein_per_kg),
            fat_pct=float(profile.fat_pct),
            selected_cut_intensity=float(
                getattr(profile, "selected_cut_intensity", getattr(profile, "cut_intensity", 0.2))
            ),
        )
    )
    _validate_profile_domain(validation_payload, effective_date)
    result = TargetResponse.model_validate(asdict(calculate_targets(profile, effective_date)))
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


def to_profile_response(
    profile: Profile, calculation_date: date | None = None
) -> ProfileResponse:
    return ProfileResponse.model_validate(
        {
            "id": profile.id,
            "sex": profile.sex,
            "birth_date": profile.birth_date,
            "height_cm": float(profile.height_cm),
            "weight_kg": float(profile.weight_kg),
            "activity_level": profile.activity_level,
            "goal": profile.goal,
            "protein_per_kg": float(profile.protein_per_kg),
            "fat_pct": float(profile.fat_pct),
            "selected_cut_intensity": float(profile.cut_intensity),
            "updated_at": profile.updated_at,
            "targets": to_target_response(profile, calculation_date),
        }
    )


def get_profile(session: Session, principal: PrincipalContext) -> Profile | None:
    return session.exec(
        select(Profile).where(Profile.principal_id == principal.principal_id)
    ).first()


def upsert_profile(
    session: Session,
    principal: PrincipalContext,
    payload: ProfileUpsert,
    calculation_date: date,
) -> ProfileResponse:
    try:
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
        session.flush()
        response = to_profile_response(profile, calculation_date)
        session.commit()
        return response
    except Exception:
        session.rollback()
        raise


def preview_targets(payload: ProfilePreview, calculation_date: date | None = None) -> TargetResponse:
    return to_target_response(payload, calculation_date)
