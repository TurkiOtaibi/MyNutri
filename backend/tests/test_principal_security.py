from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from sqlalchemy import Delete, Insert, Select, Update, event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.auth import AuthClaims, SupabaseTokenVerifier, get_token_verifier
from app.core.config import Settings, validate_runtime_configuration
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.main import app
from app.models import (
    DiaryEntry,
    Principal,
    PrincipalRole,
    PrincipalStatus,
    TargetPlan,
    TargetPlanStatus,
    TargetProvenance,
)

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


def _activate_target(
    client: TestClient, payload: dict, idempotency_key: str
) -> dict:
    preview = client.post("/profile/preview", json=payload, headers=headers("user-b"))
    assert preview.status_code == 200, preview.text
    response = client.post(
        "/target-plans/activate",
        json={
            **payload,
            "confirmed": True,
            "expected_preview_hash": preview.json()["preview_hash"],
        },
        headers={**headers("user-b"), "Idempotency-Key": idempotency_key},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _seed_active_and_due_targets(
    client: TestClient, session: Session
) -> tuple[dict, dict]:
    _activate_target(client, profile_payload(70), "active-target")
    due_response = _activate_target(client, profile_payload(67), "due-target")
    today = current_diary_date()
    plans = session.exec(
        select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_B)
    ).all()
    active = next(plan for plan in plans if plan.status == TargetPlanStatus.active)
    due = next(plan for plan in plans if plan.status == TargetPlanStatus.scheduled)
    active.effective_from = today - timedelta(days=2)
    active.effective_to = today - timedelta(days=1)
    due.effective_from = today
    session.add(active)
    session.add(due)
    session.commit()
    lifecycle = {
        plan.id: (
            plan.status,
            plan.effective_from,
            plan.effective_to,
            plan.activated_at,
            plan.closed_at,
            plan.superseded_at,
        )
        for plan in (active, due)
    }
    return due_response, lifecycle


def _install_admin_read_guards(monkeypatch, session: Session):
    engine = session.get_bind()
    statements: list[str] = []

    def fail_lifecycle(*_args, **_kwargs) -> None:
        raise AssertionError("admin monitoring invoked lifecycle advancement")

    def reject_writes(
        _conn, clauseelement, _multiparams, _params, _execution_options
    ) -> None:
        if (
            isinstance(clauseelement, Select)
            and clauseelement._for_update_arg is not None
        ):
            raise AssertionError("admin monitoring issued SELECT FOR UPDATE")
        if isinstance(clauseelement, (Insert, Update, Delete)):
            raise AssertionError("admin monitoring issued DML")
        normalized = " ".join(str(clauseelement).split()).lower()
        if normalized.startswith(("insert ", "update ", "delete ")):
            raise AssertionError("admin monitoring issued textual DML")

    def capture_cursor(
        _conn, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        statements.append(" ".join(statement.split()))

    monkeypatch.setattr("app.services.target_plans._advance_lifecycle", fail_lifecycle)
    event.listen(engine, "before_execute", reject_writes)
    event.listen(engine, "before_cursor_execute", capture_cursor)

    def cleanup() -> None:
        event.remove(engine, "before_execute", reject_writes)
        event.remove(engine, "before_cursor_execute", capture_cursor)

    return engine, statements, cleanup


def _assert_lifecycle_unchanged(engine, expected: dict) -> None:
    with Session(engine) as fresh_session:
        actual = {
            plan.id: (
                plan.status,
                plan.effective_from,
                plan.effective_to,
                plan.activated_at,
                plan.closed_at,
                plan.superseded_at,
            )
            for plan in fresh_session.exec(
                select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_B)
            ).all()
        }
    assert actual == expected


def _reject_admin_commit(monkeypatch, session: Session) -> None:
    def fail_commit() -> None:
        raise AssertionError("admin monitoring committed its transaction")

    monkeypatch.setattr(session, "commit", fail_commit)


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
    assert (
        client.get(
            f"/admin/users/{PRINCIPAL_B}", headers=headers("user-b")
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/admin/users/{PRINCIPAL_B}/diary/week",
            params={"start": current_diary_date().isoformat()},
            headers=headers("user-b"),
        ).status_code
        == 403
    )
    listing = client.get("/admin/users", headers=headers("admin-a"))
    detail = client.get(f"/admin/users/{PRINCIPAL_B}", headers=headers("admin-a"))
    assert listing.status_code == detail.status_code == 200
    assert listing.json()["total"] == 2
    assert detail.json()["account"]["principal_id"] == str(PRINCIPAL_B)
    assert client.put(
        f"/admin/users/{PRINCIPAL_B}/profile",
        json=profile_payload(),
        headers=headers("admin-a"),
    ).status_code in {404, 405}


@pytest.mark.parametrize(
    "endpoint",
    ["detail", "week", "diary", "target_history"],
)
def test_admin_monitoring_gets_execute_no_dml(
    security_context, monkeypatch, endpoint: str
) -> None:
    client, session = security_context
    due_response, lifecycle = _seed_active_and_due_targets(client, session)
    due_plan = due_response["plan"]
    today = current_diary_date()
    paths = {
        "detail": f"/admin/users/{PRINCIPAL_B}",
        "week": (
            f"/admin/users/{PRINCIPAL_B}/diary/week?start={today.isoformat()}"
        ),
        "diary": f"/admin/users/{PRINCIPAL_B}/diary?entry_date={today.isoformat()}",
        "target_history": f"/admin/users/{PRINCIPAL_B}/target-plans",
    }
    path = paths[endpoint]
    engine, statements, cleanup = _install_admin_read_guards(monkeypatch, session)
    _reject_admin_commit(monkeypatch, session)
    try:
        response_documents = []
        for _ in range(2):
            response = client.get(path, headers=headers("admin-a"))
            assert response.status_code == 200, response.text
            response_documents.append(response.json())
            if endpoint == "detail":
                assert response.json()["current_target"]["plan"]["id"] == due_plan["id"]
                assert response.json()["pending_plan"] is None
            elif endpoint == "week":
                today_summary = next(
                    day
                    for day in response.json()["days"]
                    if day["date"] == today.isoformat()
                )
                assert (
                    today_summary["targets"]["final_target_calories"]
                    == due_plan["targets"]["final_target_calories"]
                )
            elif endpoint == "diary":
                assert response.json() == []
            else:
                assert response.json()["items"][0]["id"] == due_plan["id"]
            _assert_lifecycle_unchanged(engine, lifecycle)
        assert response_documents[0] == response_documents[1]
    finally:
        cleanup()

    normalized = [statement.lower() for statement in statements]
    assert not any(
        statement.startswith(("insert ", "update ", "delete "))
        for statement in normalized
    )
    assert not any(" for update" in statement for statement in normalized)


def test_admin_week_failure_executes_no_dml(security_context, monkeypatch) -> None:
    client, session = security_context
    _, lifecycle = _seed_active_and_due_targets(client, session)
    today = current_diary_date()
    week_start = today - timedelta(days=(today.weekday() + 1) % 7)
    session.add(
        DiaryEntry(
            principal_id=PRINCIPAL_B,
            entry_date=week_start + timedelta(days=6),
            quantity=1,
            snapshot_schema_version=2,
            target_provenance=TargetProvenance.no_target_source,
            nutrition_snapshot={"schema_version": 2},
        )
    )
    session.commit()
    engine, statements, cleanup = _install_admin_read_guards(monkeypatch, session)
    _reject_admin_commit(monkeypatch, session)
    try:
        response = client.get(
            f"/admin/users/{PRINCIPAL_B}/diary/week?start={today.isoformat()}",
            headers=headers("admin-a"),
        )
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "DIARY_SUMMARY_DATA_INTEGRITY_ERROR"
        _assert_lifecycle_unchanged(engine, lifecycle)
    finally:
        cleanup()

    normalized = [statement.lower() for statement in statements]
    assert not any(
        statement.startswith(("insert ", "update ", "delete "))
        for statement in normalized
    )
    assert not any(" for update" in statement for statement in normalized)


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


def test_supabase_verifier_rejects_signed_non_uuid_subject(monkeypatch) -> None:
    settings = Settings(environment="test", supabase_url="https://project.supabase.co")
    verifier = SupabaseTokenVerifier(settings)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        verifier.jwks,
        "get_signing_key_from_jwt",
        lambda _token: SimpleNamespace(key=private_key.public_key()),
    )

    with pytest.raises(ValueError):
        verifier.verify(_jwt(verifier, private_key, sub="not-a-uuid"))


@pytest.mark.parametrize(
    "resolver_error",
    [
        PyJWKClientConnectionError("internal provider response detail"),
        PyJWKClientError("internal key algorithm mismatch detail"),
    ],
)
def test_jwks_resolver_failure_keeps_uniform_public_credential_error(
    security_context, resolver_error
) -> None:
    client, _ = security_context

    class FailingVerifier:
        def verify(self, _token: str) -> AuthClaims:
            raise resolver_error

    app.dependency_overrides[get_token_verifier] = FailingVerifier
    response = client.get("/foods", headers=headers("unresolvable-jwks"))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIAL"
    assert "provider" not in response.text


def test_production_auth_and_cors_configuration_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        validate_runtime_configuration(Settings(environment="production"))
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(allowed_origins=["*"])
