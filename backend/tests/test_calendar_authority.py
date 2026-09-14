from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import PrincipalContext, get_principal_context, get_token_verifier
from app.core.calendar import diary_calendar_authority, following_diary_date
from app.main import app
from app.schemas import TargetPlanPreviewRequest, TargetResponse
from app.api.routes.profile import preview_profile


def test_calendar_authority_before_and_after_riyadh_midnight() -> None:
    before = diary_calendar_authority(
        datetime(2026, 7, 22, 20, 59, 59, 999999, tzinfo=timezone.utc)
    )
    after = diary_calendar_authority(
        datetime(2026, 7, 22, 21, 0, 0, tzinfo=timezone.utc)
    )

    assert before.current_diary_date == date(2026, 7, 22)
    assert before.calendar_timezone == "Asia/Riyadh"
    assert before.next_rollover_at.isoformat() == "2026-07-23T00:00:00+03:00"
    assert after.current_diary_date == date(2026, 7, 23)
    assert after.calendar_timezone == "Asia/Riyadh"
    assert after.next_rollover_at.isoformat() == "2026-07-24T00:00:00+03:00"


def test_calendar_authority_rejects_naive_instants() -> None:
    with pytest.raises(ValueError, match="aware datetime"):
        diary_calendar_authority(datetime(2026, 7, 23, 0, 0, 0))


@pytest.mark.parametrize(
    ("current_date", "expected"),
    [
        (date(2026, 7, 31), date(2026, 8, 1)),
        (date(2026, 12, 31), date(2027, 1, 1)),
    ],
)
def test_plan010_following_diary_date_rolls_over(
    current_date: date, expected: date
) -> None:
    assert following_diary_date(current_date) == expected


def test_plan010_following_date_uses_each_riyadh_midnight_snapshot() -> None:
    before = diary_calendar_authority(
        datetime(2026, 12, 31, 20, 59, 59, 999999, tzinfo=timezone.utc)
    )
    after = diary_calendar_authority(
        datetime(2026, 12, 31, 21, 0, 0, tzinfo=timezone.utc)
    )

    assert following_diary_date(before.current_diary_date) == date(2027, 1, 1)
    assert following_diary_date(after.current_diary_date) == date(2027, 1, 2)


def test_authenticated_calendar_endpoint_has_stable_shape(monkeypatch) -> None:
    fixed = diary_calendar_authority(
        datetime(2026, 7, 22, 21, 0, 0, tzinfo=timezone.utc)
    )
    monkeypatch.setattr("app.api.routes.account.diary_calendar_authority", lambda: fixed)
    app.dependency_overrides[get_principal_context] = lambda: PrincipalContext(
        principal_id=UUID("00000000-0000-0000-0000-00000000000a")
    )
    try:
        with TestClient(app) as client:
            response = client.get(
                "/account/calendar", headers={"Authorization": "Bearer test-token"}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "current_diary_date": "2026-07-23",
        "calendar_timezone": "Asia/Riyadh",
        "next_rollover_at": "2026-07-24T00:00:00+03:00",
    }


def test_calendar_endpoint_requires_authentication() -> None:
    app.dependency_overrides[get_token_verifier] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/account/calendar")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def _plan008_payload() -> TargetPlanPreviewRequest:
    return TargetPlanPreviewRequest(
        effective_from=date(2026, 7, 24),
        sex="male",
        birth_date=date(1990, 1, 1),
        height_cm=175,
        weight_kg=80,
        activity_level="moderate",
        goal="maintain",
        protein_per_kg=1.2,
        fat_pct=0.25,
        selected_cut_intensity=0.2,
    )


def test_preview_uses_the_explicit_effective_date(monkeypatch) -> None:
    captured_date = None

    def preview(payload, effective_date):
        nonlocal captured_date
        captured_date = effective_date
        return TargetResponse.model_construct()

    monkeypatch.setattr("app.api.routes.profile.preview_targets", preview)

    payload = _plan008_payload()
    preview_profile(payload, PrincipalContext(UUID(int=10)), object())

    assert captured_date == payload.effective_from
