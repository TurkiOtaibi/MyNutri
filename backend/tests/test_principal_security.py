from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.auth import AuthClaims, SupabaseTokenVerifier, get_token_verifier
from app.core.config import Settings, validate_runtime_configuration
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.main import app
from app.models import Principal, PrincipalRole, PrincipalStatus

PRINCIPAL_A = UUID("00000000-0000-0000-0000-00000000000a")
PRINCIPAL_B = UUID("00000000-0000-0000-0000-00000000000b")
AUTH_A = UUID("10000000-0000-0000-0000-00000000000a")
AUTH_B = UUID("10000000-0000-0000-0000-00000000000b")
AUTH_NEW = UUID("10000000-0000-0000-0000-00000000000c")


class FakeVerifier:
    def verify(self, token: str) -> AuthClaims:
        mapping = {
            "admin-a": AuthClaims(AUTH_A, "admin@example.com", "Admin"),
            "rotated-admin-a": AuthClaims(AUTH_A, "admin@example.com", "Admin"),
            "user-b": AuthClaims(AUTH_B, "user@example.com", "User B"),
            "new-user": AuthClaims(AUTH_NEW, "new@example.com", "New User"),
        }
        if token not in mapping:
            raise ValueError("invalid token")
        return mapping[token]


def profile_payload(weight: float = 80) -> dict:
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


def food_payload(name: str = "Shared food") -> dict:
    return {
        "name": name,
        "food_category_key": "other",
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
def security_context():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        Principal(
            id=PRINCIPAL_A,
            auth_user_id=AUTH_A,
            email="admin@example.com",
            role=PrincipalRole.admin,
        )
    )
    session.add(
        Principal(
            id=PRINCIPAL_B,
            auth_user_id=AUTH_B,
            email="user@example.com",
            role=PrincipalRole.user,
        )
    )
    session.commit()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_token_verifier] = FakeVerifier
    client = TestClient(app)
    try:
        yield client, session
    finally:
        app.dependency_overrides.clear()
        client.close()
        session.close()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_invalid_and_unsupported_credentials(security_context) -> None:
    client, _ = security_context
    missing = client.get("/foods")
    invalid = client.get("/foods", headers=headers("wrong"))
    unsupported = client.get("/foods", headers={"Authorization": "Basic value"})
    assert missing.status_code == invalid.status_code == unsupported.status_code == 401
    assert missing.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert invalid.json()["detail"]["code"] == "INVALID_CREDENTIAL"
    assert unsupported.json()["detail"]["code"] == "INVALID_CREDENTIAL"


def test_valid_token_rotation_and_account_response(security_context) -> None:
    client, _ = security_context
    first = client.get("/account/me", headers=headers("admin-a"))
    rotated = client.get("/account/me", headers=headers("rotated-admin-a"))
    assert first.status_code == rotated.status_code == 200
    assert first.json()["principal_id"] == rotated.json()["principal_id"] == str(PRINCIPAL_A)
    assert first.json()["role"] == "admin"


def test_unknown_auth_user_is_provisioned_as_user_idempotently(security_context) -> None:
    client, session = security_context
    first = client.get("/account/me", headers=headers("new-user"))
    second = client.get("/account/me", headers=headers("new-user"))
    assert first.status_code == second.status_code == 200
    assert first.json()["principal_id"] == second.json()["principal_id"]
    principal = session.get(Principal, UUID(first.json()["principal_id"]))
    assert principal and principal.role == PrincipalRole.user


def test_disabled_principal_is_rejected(security_context) -> None:
    client, session = security_context
    principal = session.get(Principal, PRINCIPAL_B)
    assert principal
    principal.status = PrincipalStatus.disabled
    session.add(principal)
    session.commit()
    response = client.get("/foods", headers=headers("user-b"))
    assert response.status_code == 401


def test_profile_diary_and_target_plan_isolation(security_context) -> None:
    client, _ = security_context
    a_profile = client.put("/profile", json=profile_payload(82), headers=headers("admin-a"))
    b_profile = client.put("/profile", json=profile_payload(67), headers=headers("user-b"))
    assert a_profile.status_code == b_profile.status_code == 200
    assert a_profile.json()["id"] != b_profile.json()["id"]
    assert client.get("/profile", headers=headers("admin-a")).json()["weight_kg"] == 82
    assert client.get("/profile", headers=headers("user-b")).json()["weight_kg"] == 67
    assert client.get("/diary", headers=headers("admin-a")).json() == []
    assert client.get("/diary", headers=headers("user-b")).json() == []
    assert client.get("/target-plans", headers=headers("admin-a")).status_code == 200
    assert client.get("/target-plans", headers=headers("user-b")).status_code == 200


def test_shared_catalog_and_admin_only_mutations(security_context) -> None:
    client, _ = security_context
    denied = client.post("/foods", json=food_payload(), headers=headers("user-b"))
    assert denied.status_code == 403
    created = client.post("/foods", json=food_payload(), headers=headers("admin-a"))
    assert created.status_code == 201, created.text
    food_id = created.json()["id"]
    assert client.get("/foods", headers=headers("user-b")).json()[0]["id"] == food_id
    assert client.get(f"/foods/{food_id}", headers=headers("user-b")).status_code == 200
    assert client.put(f"/foods/{food_id}", json={"name": "No"}, headers=headers("user-b")).status_code == 403
    assert client.delete(f"/foods/{food_id}", headers=headers("user-b")).status_code == 403


def test_admin_archive_restore_and_history_safe_delete(security_context) -> None:
    client, _ = security_context
    created = client.post(
        "/foods", json=food_payload("Historically used"), headers=headers("admin-a")
    ).json()
    diary = client.post(
        "/diary",
        json={
            "food_id": created["id"],
            "entry_date": current_diary_date().isoformat(),
            "quantity": 1,
            "meal_type": "breakfast",
        },
        headers=headers("user-b"),
    )
    assert diary.status_code == 201, diary.text
    deletion = client.delete(f"/admin/foods/{created['id']}", headers=headers("admin-a"))
    assert deletion.status_code == 200
    assert deletion.json()["disposition"] == "archived"
    assert client.get(f"/foods/{created['id']}", headers=headers("user-b")).status_code == 404
    assert client.get(f"/admin/foods/{created['id']}", headers=headers("admin-a")).status_code == 200
    restored = client.post(
        f"/admin/foods/{created['id']}/restore", headers=headers("admin-a")
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_admin_monitoring_is_authorized_and_read_only(security_context) -> None:
    client, _ = security_context
    assert client.get("/admin/users", headers=headers("user-b")).status_code == 403
    listing = client.get("/admin/users", headers=headers("admin-a"))
    detail = client.get(f"/admin/users/{PRINCIPAL_B}", headers=headers("admin-a"))
    assert listing.status_code == detail.status_code == 200
    assert listing.json()["total"] == 2
    assert client.put(
        f"/admin/users/{PRINCIPAL_B}/profile",
        json=profile_payload(),
        headers=headers("admin-a"),
    ).status_code in {404, 405}


def test_client_authoritative_identity_and_role_are_rejected(security_context) -> None:
    client, _ = security_context
    for field in ("principal_id", "owner_id", "user_id", "role"):
        payload = profile_payload()
        payload[field] = "admin"
        assert client.put("/profile", json=payload, headers=headers("user-b")).status_code == 422


def test_openapi_declares_http_bearer_security() -> None:
    app.openapi_schema = None
    schema = app.openapi()
    scheme = schema["components"]["securitySchemes"]["BearerAuth"]
    assert scheme["type"] == "http" and scheme["scheme"] == "bearer"
    assert schema["paths"]["/admin/users"]["get"]["security"] == [{"BearerAuth": []}]
    assert schema["paths"]["/foods"]["get"]["security"] == [{"BearerAuth": []}]


def _jwt(verifier: SupabaseTokenVerifier, private_key, **overrides) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(AUTH_A),
        "email": "admin@example.com",
        "iss": verifier.issuer,
        "aud": verifier.audience,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test"})


def test_supabase_verifier_validates_signature_expiry_issuer_and_audience(monkeypatch) -> None:
    settings = Settings(environment="test", supabase_url="https://project.supabase.co")
    verifier = SupabaseTokenVerifier(settings)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        verifier.jwks,
        "get_signing_key_from_jwt",
        lambda _token: SimpleNamespace(key=private_key.public_key()),
    )
    assert verifier.verify(_jwt(verifier, private_key)).auth_user_id == AUTH_A
    bad_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(jwt.InvalidSignatureError):
        verifier.verify(_jwt(verifier, bad_key))
    with pytest.raises(jwt.ExpiredSignatureError):
        verifier.verify(
            _jwt(verifier, private_key, exp=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
    with pytest.raises(jwt.InvalidIssuerError):
        verifier.verify(_jwt(verifier, private_key, iss="https://wrong.example/auth/v1"))
    with pytest.raises(jwt.InvalidAudienceError):
        verifier.verify(_jwt(verifier, private_key, aud="wrong"))


def test_production_auth_and_cors_configuration_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        validate_runtime_configuration(Settings(environment="production"))
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(allowed_origins=["*"])
