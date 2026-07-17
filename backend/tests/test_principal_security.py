from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Settings, get_settings, validate_runtime_configuration
from app.db.session import get_session
from app.main import app
from app.models import Principal

PRINCIPAL_A = UUID("00000000-0000-0000-0000-00000000000a")
PRINCIPAL_B = UUID("00000000-0000-0000-0000-00000000000b")


def _profile_payload(weight: float = 80) -> dict:
    return {
        "sex": "male",
        "birth_date": "1990-01-01",
        "height_cm": 175,
        "weight_kg": weight,
        "activity_level": "moderate",
        "goal": "maintain",
        "protein_per_kg": 1.2,
        "fat_pct": 0.25,
    }


def _food_payload(name: str = "Owner scoped food") -> dict:
    return {
        "name": name,
        "primary_category_key": "other",
        "food_kind": "simple",
        "nutrition_basis": "per_100g",
        "default_unit_type": "serving",
        "unit_amount": 100,
        "unit_basis": "g",
        "calories": 180,
        "protein_g": 10,
        "carb_g": 20,
        "fat_g": 6,
        "nutrition_source": {"type": "unknown"},
    }


@pytest.fixture
def principal_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Principal(id=PRINCIPAL_A))
    session.add(Principal(id=PRINCIPAL_B))
    session.commit()
    settings = Settings(
        environment="test",
        single_user_token="",
        principal_token_map={
            "token-a": PRINCIPAL_A,
            "rotated-token-a": PRINCIPAL_A,
            "token-b": PRINCIPAL_B,
        },
        snapshot_v2_writer_enabled=True,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        client.close()
        session.close()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_and_invalid_credentials_fail_closed(principal_client: TestClient) -> None:
    missing = principal_client.get("/foods")
    invalid = principal_client.get("/foods", headers=_headers("wrong"))

    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert invalid.json()["detail"]["code"] == "INVALID_CREDENTIAL"
    assert "WWW-Authenticate" in missing.headers


def test_profile_and_food_are_isolated_between_two_principals(
    principal_client: TestClient,
) -> None:
    created_profile = principal_client.put(
        "/profile", json=_profile_payload(), headers=_headers("token-a")
    )
    assert created_profile.status_code == 200
    updated_profile = principal_client.put(
        "/profile", json=_profile_payload(weight=81), headers=_headers("token-a")
    )
    assert updated_profile.status_code == 200
    assert updated_profile.json()["id"] == created_profile.json()["id"]
    assert principal_client.get("/profile", headers=_headers("token-b")).status_code == 404
    other_profile = principal_client.put(
        "/profile", json=_profile_payload(weight=70), headers=_headers("token-b")
    )
    assert other_profile.status_code == 200
    assert other_profile.json()["id"] != created_profile.json()["id"]

    created = principal_client.post("/foods", json=_food_payload(), headers=_headers("token-a"))
    assert created.status_code == 201
    food_id = created.json()["id"]

    missing = principal_client.get(f"/foods/{uuid4()}", headers=_headers("token-b"))
    cross_owner = principal_client.get(f"/foods/{food_id}", headers=_headers("token-b"))
    assert missing.status_code == cross_owner.status_code == 404
    assert missing.json() == cross_owner.json()
    assert principal_client.get("/foods", headers=_headers("token-b")).json() == []

    same_key_other_owner = principal_client.post(
        "/foods", json=_food_payload(), headers=_headers("token-b")
    )
    assert same_key_other_owner.status_code == 201


def test_cross_owner_mutations_and_diary_binding_are_non_enumerating(
    principal_client: TestClient,
) -> None:
    created = principal_client.post(
        "/foods", json=_food_payload("Private food"), headers=_headers("token-a")
    )
    food_id = created.json()["id"]

    update = principal_client.put(
        f"/foods/{food_id}", json={"name": "Changed"}, headers=_headers("token-b")
    )
    delete = principal_client.delete(f"/foods/{food_id}", headers=_headers("token-b"))
    diary = principal_client.post(
        "/diary",
        json={
            "food_id": food_id,
            "entry_date": "2026-01-01",
            "quantity": 1,
            "meal_type": "breakfast",
        },
        headers=_headers("token-b"),
    )

    assert update.status_code == delete.status_code == diary.status_code == 404
    assert update.json() == delete.json() == diary.json()

    own_diary = principal_client.post(
        "/diary",
        json={
            "food_id": food_id,
            "entry_date": "2026-01-01",
            "quantity": 1,
            "meal_type": "breakfast",
        },
        headers=_headers("token-a"),
    )
    assert own_diary.status_code == 201
    assert own_diary.json()["snapshot_schema_version"] == 2
    assert own_diary.json()["target_plan_id"] is None
    assert own_diary.json()["target_provenance"] == "no_target_source"
    assert "schema_version" not in own_diary.json()["nutrition_snapshot"]
    entry_id = own_diary.json()["id"]
    missing_entry = principal_client.get(f"/diary/{uuid4()}", headers=_headers("token-b"))
    cross_entry = principal_client.get(f"/diary/{entry_id}", headers=_headers("token-b"))
    assert missing_entry.status_code == cross_entry.status_code == 404
    assert missing_entry.json() == cross_entry.json()
    assert principal_client.get("/diary", headers=_headers("token-b")).json() == []
    week = principal_client.get("/diary/week?start=2026-01-01", headers=_headers("token-b"))
    assert week.status_code == 200
    assert week.json()["weekly_totals"]["calories"] == 0

    injected = principal_client.post(
        "/diary/entries",
        json={
            "food_id": food_id,
            "entry_date": "2026-01-01",
            "quantity": 1,
            "nutrition_snapshot": {"schema_version": 2},
            "target_plan_id": str(uuid4()),
        },
        headers=_headers("token-a"),
    )
    assert injected.status_code == 422
    assert {
        item["code"] for item in injected.json()["detail"]
    } == {"NON_AUTHORITATIVE_FIELD"}


def test_token_rotation_preserves_principal_ownership(principal_client: TestClient) -> None:
    created = principal_client.post(
        "/foods", json=_food_payload("Rotation food"), headers=_headers("token-a")
    )
    food_id = created.json()["id"]

    rotated_read = principal_client.get(f"/foods/{food_id}", headers=_headers("rotated-token-a"))
    assert rotated_read.status_code == 200
    assert rotated_read.json()["id"] == food_id


@pytest.mark.parametrize("field", ["principal_id", "owner_id", "user_id"])
def test_client_authoritative_owner_fields_are_rejected(
    principal_client: TestClient, field: str
) -> None:
    payload = _food_payload(f"Rejected {field}")
    payload[field] = str(PRINCIPAL_B)
    response = principal_client.post("/foods", json=payload, headers=_headers("token-a"))
    assert response.status_code == 422

    profile_payload = _profile_payload()
    profile_payload[field] = str(PRINCIPAL_B)
    assert (
        principal_client.put(
            "/profile", json=profile_payload, headers=_headers("token-a")
        ).status_code
        == 422
    )

    assert (
        principal_client.post(
            "/diary",
            json={
                "food_id": str(uuid4()),
                "entry_date": "2026-01-01",
                "quantity": 1,
                field: str(PRINCIPAL_B),
            },
            headers=_headers("token-a"),
        ).status_code
        == 422
    )


def test_production_auth_configuration_is_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="DEPLOYMENT_PRINCIPAL_ID"):
        validate_runtime_configuration(
            Settings(environment="production", single_user_token="production-secret")
        )

    with pytest.raises(RuntimeError, match="SINGLE_USER_TOKEN"):
        validate_runtime_configuration(
            Settings(
                environment="production",
                deployment_principal_id=PRINCIPAL_A,
                single_user_token="",
            )
        )


def test_application_startup_never_invokes_metadata_create_all(monkeypatch) -> None:
    def prohibited(*args, **kwargs):
        raise AssertionError("runtime create_all is prohibited")

    monkeypatch.setattr(SQLModel.metadata, "create_all", prohibited)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    with pytest.raises(RuntimeError, match="test-only"):
        validate_runtime_configuration(
            Settings(
                environment="production",
                deployment_principal_id=PRINCIPAL_A,
                single_user_token="production-secret",
                principal_token_map={"production-secret": PRINCIPAL_B},
            )
        )
