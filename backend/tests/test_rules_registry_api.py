from collections.abc import Generator
from importlib.resources import files
import json
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.main import app
from app.models import Principal
from app.nutrition_rules.manifest import canonical_manifest_bytes, rules_manifest_hash
from app.nutrition_rules.versions import VERSIONS

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app, headers={"Authorization": "Bearer dev-token"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_registry_exposes_exact_version_bundle_and_authoritative_metadata(
    client: TestClient,
) -> None:
    response = client.get("/nutrition/registry")
    assert response.status_code == 200
    body = response.json()
    assert {key: body[key] for key in VERSIONS.as_dict()} == VERSIONS.as_dict()
    assert body["rules_manifest_hash"] == rules_manifest_hash()
    assert len(body["nutrients"]) == 16
    assert len(body["target_types"]) == 7
    assert body["analysis_rules_version"] is None
    assert body["analysis_rules_status"] == "reserved_for_wave_3"
    assert body["calculation_policy"]["goal_policy"]["maximum_deficit_kcal"] == 750
    assert body["calculation_policy"]["calendar_timezone"] == "Asia/Riyadh"
    assert body["source_types"][-2] == {
        "type": "multiple_sources",
        "reliability": "mixed",
    }
    assert body["nova"] == {
        "classifications": [1, 2, 3, 4, "unknown"],
        "review_statuses": ["unreviewed", "reviewed"],
        "automated_suggestions": False,
    }
    assert response.headers["cache-control"] == "private, max-age=300, must-revalidate"


def test_registry_requires_authenticated_principal(client: TestClient) -> None:
    response = client.get("/nutrition/registry", headers={"Authorization": ""})
    assert response.status_code == 401


def test_registry_etag_and_manifest_are_deterministic(client: TestClient) -> None:
    first = client.get("/nutrition/registry")
    second = client.get("/nutrition/registry")
    assert first.headers["etag"] == second.headers["etag"] == f'"{rules_manifest_hash()}"'
    assert canonical_manifest_bytes() == canonical_manifest_bytes()
    cached = client.get("/nutrition/registry", headers={"If-None-Match": first.headers["etag"]})
    assert cached.status_code == 304
    assert cached.content == b""


def test_released_manifest_content_matches_version_lock() -> None:
    lock = json.loads(
        files("app.nutrition_rules").joinpath("rules_manifest.lock.json").read_text("utf-8")
    )
    assert lock["version_bundle"] == VERSIONS.as_dict()
    assert lock["sha256"] == rules_manifest_hash()


def test_profile_preview_exposes_calculation_provenance(client: TestClient) -> None:
    response = client.post(
        "/profile/preview",
        json={
            "sex": "male",
            "birth_date": "1996-01-01",
            "height_cm": 180,
            "weight_kg": 80,
            "activity_level": "moderate",
            "goal": "maintain",
            "protein_per_kg": 1.2,
            "fat_pct": 0.25,
            "selected_cut_intensity": 0.2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["protein_calculation"]["basis"] == "actual_weight"
    assert body["protein_calculation"]["target_g"] == body["protein_g"]
    assert "وزنك الحالي" in body["protein_calculation"]["explanation_ar"]
    assert body["carb_clamped"] is False
    assert body["calculation_engine_version"] == "2.0.0"
    assert body["nutrition_registry_version"] == "1.0.0"
    assert len(body["additional_targets"]) == 16


def test_profile_preview_rejects_non_positive_carbohydrate(client: TestClient) -> None:
    response = client.post(
        "/profile/preview",
        json={
            "sex": "female",
            "birth_date": "1926-01-01",
            "height_cm": 100,
            "weight_kg": 20,
            "activity_level": "sedentary",
            "goal": "cut",
            "protein_per_kg": 3,
            "fat_pct": 0.3,
            "selected_cut_intensity": 0.25,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NON_POSITIVE_CARBOHYDRATE_ALLOCATION"
    assert response.json()["error"]["dimension"] == "macro_allocation"


def test_profile_preview_returns_blocked_safety_outcome_without_override(
    client: TestClient,
) -> None:
    response = client.post(
        "/profile/preview",
        json={
            "sex": "female",
            "birth_date": "1946-01-01",
            "height_cm": 160,
            "weight_kg": 60,
            "activity_level": "sedentary",
            "goal": "cut",
            "protein_per_kg": 1.2,
            "fat_pct": 0.3,
            "selected_cut_intensity": 0.2,
        },
    )
    assert response.status_code == 200
    assert 800 <= response.json()["final_target_calories"] <= 1200
    assert response.json()["safety_outcome"] == "specialist_review_required"
    assert response.json()["can_activate"] is False


def test_frontend_contains_no_authoritative_nutrient_target_registry() -> None:
    source = (Path(__file__).resolve().parents[2] / "frontend/lib/nutrients.ts").read_text("utf-8")
    assert "additionalNutrients" not in source
    assert "targetValue: 30" not in source
    assert "percent_of_calories" not in source
