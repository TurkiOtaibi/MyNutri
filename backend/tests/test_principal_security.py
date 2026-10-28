from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Delete, Insert, Select, Update, event, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.auth import PrincipalContext
from app.core.config import Settings, validate_runtime_configuration
from app.services.internal_auth import token_digest
from app.core.calendar import current_diary_date
from app.db.session import get_session
from app.main import app
from app.models import (
    AuthSession,
    DiaryEntry,
    Principal,
    PrincipalRole,
    PrincipalStatus,
    Profile,
    TargetPlan,
)
from app.schemas import ProfileUpsert
from app.schemas import TargetPlanWriteRequest
from app.services.diary import _lock_owner_for_target_binding
from app.services.food import _lock_food_namespace
from app.services.target_plans import TargetPlanError, write_target_plan

PRINCIPAL_A = UUID("00000000-0000-0000-0000-00000000000a")
PRINCIPAL_B = UUID("00000000-0000-0000-0000-00000000000b")
AUTH_A = UUID("10000000-0000-0000-0000-00000000000a")
AUTH_B = UUID("10000000-0000-0000-0000-00000000000b")
AUTH_NEW = UUID("10000000-0000-0000-0000-00000000000c")


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
        "primary_category": "other",
        "subcategory": "other",
        "nutrition_basis": "per_100g",
        "default_unit_type": "serving",
        "unit_amount": 100,
        "unit_basis": "g",
        "calories": 180,
        "protein_g": 10,
        "carb_g": 20,
        "fat_g": 6,
        "nutrition_data_source": "estimated",
    }


@pytest.fixture
def security_context():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    event.listen(
        engine,
        "connect",
        lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
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

    now = datetime.now(timezone.utc)
    for label, owner in (("admin-a", PRINCIPAL_A), ("rotated-admin-a", PRINCIPAL_A),
                         ("user-b", PRINCIPAL_B), ("fresh-user", PRINCIPAL_B)):
        session.add(AuthSession(principal_id=owner, token_hash=token_digest(_token(label)),
                                created_at=now, last_used_at=now,
                                expires_at=now + timedelta(days=30)))
    session.commit()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        yield client, session
    finally:
        app.dependency_overrides.clear()
        client.close()
        session.close()


def _token(label: str) -> str:
    return "mn1_" + base64.urlsafe_b64encode(hashlib.sha256(label.encode()).digest()).decode().rstrip("=")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(token)}"}


def test_admin_account_create_is_backend_only_and_normal_user_forbidden(security_context) -> None:
    client, session = security_context

    payload = {
        "username": "created",
        "display_name": "Created User",
        "initial_password": "synthetic-password",
    }
    denied = client.post(
        "/admin/accounts",
        json=payload,
        headers={**headers("user-b"), "Idempotency-Key": "create-test"},
    )
    assert denied.status_code == 403
    created = client.post(
        "/admin/accounts",
        json=payload,
        headers={**headers("admin-a"), "Idempotency-Key": "create-test"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "active"
    assert "password" not in created.text
    assert session.exec(select(Principal).where(Principal.username == "created")).one().auth_user_id is None


def test_private_writers_recheck_active_status_after_authentication(security_context) -> None:
    _, session = security_context
    user = session.get(Principal, PRINCIPAL_B)
    user.status = PrincipalStatus.deleting
    session.add(user)
    session.commit()
    context = PrincipalContext(principal_id=PRINCIPAL_B, auth_user_id=AUTH_B)
    with pytest.raises(Exception) as diary_error:
        _lock_owner_for_target_binding(session, context)
    assert getattr(diary_error.value, "status_code", None) == 401
    payload = TargetPlanWriteRequest.model_validate({
        **profile_payload(),
        "effective_from": current_diary_date().isoformat(),
        "confirmed": True,
        "expected_preview_hash": "0" * 64,
    })
    with pytest.raises(TargetPlanError) as plan_error:
        write_target_plan(session, context, payload, "locked-writer-test")
    assert plan_error.value.status_code == 401
    admin = session.get(Principal, PRINCIPAL_A)
    admin.status = PrincipalStatus.disabled
    session.add(admin)
    session.commit()
    with pytest.raises(Exception) as food_error:
        _lock_food_namespace(session, PrincipalContext(principal_id=PRINCIPAL_A, auth_user_id=AUTH_A, role=PrincipalRole.admin))
    assert getattr(food_error.value, "status_code", None) == 401


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/admin/accounts", None),
        ("post", "/admin/accounts", {"username": "example", "display_name": "X", "initial_password": "password"}),
        ("patch", f"/admin/accounts/{PRINCIPAL_A}", {"display_name": "Changed"}),
        ("put", f"/admin/accounts/{PRINCIPAL_A}/password", {"new_password": "password"}),
        ("put", f"/admin/accounts/{PRINCIPAL_A}/status", {"enabled": False}),
        ("delete", f"/admin/accounts/{PRINCIPAL_A}", {"confirm_email": "admin@example.com"}),
    ],
)
def test_account_management_authorization_matrix(security_context, method, path, payload) -> None:
    client, _ = security_context
    user_response = client.request(method, path, json=payload, headers={**headers("user-b"), "Idempotency-Key": "auth-matrix"})
    assert user_response.status_code == 403
    if path != "/admin/accounts":
        admin_response = client.request(method, path, json=payload, headers=headers("admin-a"))
        assert admin_response.status_code == 403


def test_admin_create_rejects_role_and_sanitizes_password_validation(security_context) -> None:
    client, _ = security_context
    password = "synthetic-private-password"
    response = client.post(
        "/admin/accounts",
        json={"username": "newuser", "display_name": "New", "initial_password": password, "role": "admin"},
        headers={**headers("admin-a"), "Idempotency-Key": "extra-field"},
    )
    assert response.status_code == 422
    assert password not in response.text
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_late_retired_provider_identity_is_never_admitted(security_context) -> None:
    client, session = security_context
    session.add(Principal(status=PrincipalStatus.deleted, retired_auth_user_id=AUTH_NEW))
    session.commit()
    response = client.get("/account/me", headers=headers("new-user"))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIAL"


def test_admin_account_crud_and_typed_username_confirmation(security_context) -> None:
    client, session = security_context

    admin = headers("admin-a")
    created = client.post(
        "/admin/accounts",
        json={"username": "lifecycle", "display_name": "First", "initial_password": "password"},
        headers={**admin, "Idempotency-Key": "full-crud"},
    )
    assert created.status_code == 201
    principal_id = created.json()["principal_id"]
    edited = client.patch(f"/admin/accounts/{principal_id}", json={"display_name": "Second"}, headers=admin)
    assert edited.status_code == 200 and edited.json()["display_name"] == "Second"
    reset = client.put(f"/admin/accounts/{principal_id}/password", json={"new_password": "new-password"}, headers=admin)
    assert reset.status_code == 204
    disabled = client.put(f"/admin/accounts/{principal_id}/status", json={"enabled": False}, headers=admin)
    assert disabled.status_code == 200 and disabled.json()["status"] == "disabled"
    enabled = client.put(f"/admin/accounts/{principal_id}/status", json={"enabled": True}, headers=admin)
    assert enabled.status_code == 200 and enabled.json()["status"] == "active"
    mismatch = client.request("DELETE", f"/admin/accounts/{principal_id}", json={"confirm_username": "wrong"}, headers=admin)
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["message_ar"] == "اسم المستخدم المدخل لا يطابق هذا الحساب."
    deleted = client.request("DELETE", f"/admin/accounts/{principal_id}", json={"confirm_username": "lifecycle"}, headers=admin)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == "deleted"
    assert deleted.json()["email"] is None
    assert session.get(Principal, UUID(principal_id)).username is None
    listing = client.get("/admin/accounts", headers=admin)
    assert listing.status_code == 200
    assert all(item["principal_id"] != principal_id for item in listing.json()["items"])


def test_admin_account_list_filters_by_search_and_status(security_context) -> None:
    client, session = security_context
    for email, name, status in [
        ("sara@example.com", "Sara", PrincipalStatus.active),
        ("khalid@example.com", "خالد", PrincipalStatus.disabled),
        ("pending@example.com", "Sara Pending", PrincipalStatus.provisioning),
        ("stuck@example.com", "Stuck", PrincipalStatus.deleting),
        (None, None, PrincipalStatus.deleted),
    ]:
        session.add(Principal(email=email, display_name=name, role=PrincipalRole.user, status=status))
    session.commit()
    admin = headers("admin-a")

    def emails(query: str) -> tuple[int, set[str | None]]:
        response = client.get(f"/admin/accounts{query}", headers=admin)
        assert response.status_code == 200, response.text
        body = response.json()
        return body["total"], {item["email"] for item in body["items"]}

    assert emails("") == (5, {"user@example.com", "sara@example.com", "khalid@example.com",
                              "pending@example.com", "stuck@example.com"})
    assert emails("?search=sara") == (2, {"sara@example.com", "pending@example.com"})
    assert emails("?search=%20SARA%20") == (2, {"sara@example.com", "pending@example.com"})
    assert emails("?search=خالد") == (1, {"khalid@example.com"})
    assert emails("?search=admin") == (0, set())
    assert emails("?status=deleting") == (1, {"stuck@example.com"})
    assert emails("?status=provisioning&search=sara") == (1, {"pending@example.com"})
    assert emails("?status=deleted") == (0, set())
    assert client.get("/admin/accounts?status=unknown", headers=admin).status_code == 422
    assert client.get("/admin/accounts?search=sara", headers=headers("user-b")).status_code == 403


def _seed_profile(session: Session, principal_id: UUID, payload: dict) -> Profile:
    validated = ProfileUpsert.model_validate(payload)
    data = validated.model_dump()
    data["cut_intensity"] = data.pop("selected_cut_intensity")
    profile = Profile(principal_id=principal_id, **data)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def _write_target(client: TestClient, payload: dict, idempotency_key: str) -> dict:
    effective_from = current_diary_date().isoformat()
    preview = client.post(
        "/profile/preview",
        json={**payload, "effective_from": effective_from},
        headers=headers("user-b"),
    )
    assert preview.status_code == 200, preview.text
    response = client.post(
        "/target-plans",
        json={
            **payload,
            "effective_from": effective_from,
            "confirmed": True,
            "expected_preview_hash": preview.json()["preview_hash"],
        },
        headers={**headers("user-b"), "Idempotency-Key": idempotency_key},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _seed_current_target_revisions(client: TestClient, session: Session) -> tuple[dict, dict]:
    _write_target(client, profile_payload(70), "target-revision-1")
    current_response = _write_target(client, profile_payload(67), "target-revision-2")
    plans = session.exec(select(TargetPlan).where(TargetPlan.principal_id == PRINCIPAL_B)).all()
    plan_state = {
        plan.id: (
            plan.effective_from,
            plan.revision,
            plan.calculation_document,
            plan.created_at,
        )
        for plan in plans
    }
    return current_response, plan_state


def _install_admin_read_guards(monkeypatch, session: Session):
    engine = session.get_bind()
    statements: list[str] = []

    def reject_writes(_conn, clauseelement, _multiparams, _params, _execution_options) -> None:
        if isinstance(clauseelement, Select) and clauseelement._for_update_arg is not None:
            raise AssertionError("admin monitoring issued SELECT FOR UPDATE")
        if isinstance(clauseelement, (Insert, Update, Delete)):
            raise AssertionError("admin monitoring issued DML")
        normalized = " ".join(str(clauseelement).split()).lower()
        if normalized.startswith(("insert ", "update ", "delete ")):
            raise AssertionError("admin monitoring issued textual DML")

    def capture_cursor(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(" ".join(statement.split()))

    def reject_flush(*_args, **_kwargs) -> None:
        raise AssertionError("admin monitoring flushed its transaction")

    event.listen(engine, "before_execute", reject_writes)
    event.listen(engine, "before_cursor_execute", capture_cursor)
    event.listen(session, "before_flush", reject_flush)

    def cleanup() -> None:
        event.remove(engine, "before_execute", reject_writes)
        event.remove(engine, "before_cursor_execute", capture_cursor)
        event.remove(session, "before_flush", reject_flush)

    return engine, statements, cleanup


def _assert_plans_unchanged(engine, expected: dict) -> None:
    with Session(engine) as fresh_session:
        actual = {
            plan.id: (
                plan.effective_from,
                plan.revision,
                plan.calculation_document,
                plan.created_at,
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


def test_unknown_auth_user_is_rejected_without_creating_principal(security_context) -> None:
    client, session = security_context
    first = client.get("/account/me", headers=headers("new-user"))
    second = client.get("/account/me", headers=headers("new-user"))
    assert first.status_code == second.status_code == 401
    assert first.json()["detail"]["code"] == "INVALID_CREDENTIAL"
    assert session.exec(select(Principal).where(Principal.auth_user_id == AUTH_NEW)).first() is None


@pytest.mark.parametrize("status", ["provisioning", "disabled", "deleting", "deleted"])
def test_non_active_principal_is_rejected(security_context, status: str) -> None:
    client, session = security_context
    principal = session.get(Principal, PRINCIPAL_B)
    assert principal
    principal.status = PrincipalStatus(status)
    session.add(principal)
    session.commit()
    response = client.get("/account/me", headers=headers("user-b"))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == ("ACCOUNT_DISABLED" if status == "disabled" else "INVALID_CREDENTIAL")


def test_revoked_sessions_rejected_while_other_session_remains_active(security_context) -> None:
    client, session = security_context
    current = session.exec(select(AuthSession).where(AuthSession.token_hash == token_digest(_token("user-b")))).one()
    current.revoked_at = datetime.now(timezone.utc)
    session.add(current)
    session.commit()
    assert client.get("/account/me", headers=headers("user-b")).status_code == 401
    assert client.get("/account/me", headers=headers("fresh-user")).status_code == 200


def test_unknown_session_is_rejected_even_without_revocation(security_context) -> None:
    client, _ = security_context
    response = client.get("/account/me", headers=headers("unknown-session"))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIAL"


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
    client, session = security_context
    a_profile = _seed_profile(session, PRINCIPAL_A, profile_payload(82))
    b_profile = _seed_profile(session, PRINCIPAL_B, profile_payload(67))
    assert a_profile.id != b_profile.id
    assert client.get("/profile", headers=headers("admin-a")).json()["weight_kg"] == 82
    assert client.get("/profile", headers=headers("user-b")).json()["weight_kg"] == 67
    assert client.get("/diary/entries", headers=headers("admin-a")).json() == []
    assert client.get("/diary/entries", headers=headers("user-b")).json() == []
    assert client.get("/target-plans", headers=headers("admin-a")).status_code == 200
    assert client.get("/target-plans", headers=headers("user-b")).status_code == 200


def test_shared_catalog_and_admin_only_mutations(security_context) -> None:
    client, _ = security_context
    denied = client.post("/foods", json=food_payload(), headers=headers("user-b"))
    assert denied.status_code == 403
    created = client.post("/foods", json=food_payload(), headers=headers("admin-a"))
    assert created.status_code == 201, created.text
    food_id = created.json()["id"]
    assert client.get("/foods", headers=headers("user-b")).json()["items"][0]["id"] == food_id
    assert client.get(f"/foods/{food_id}", headers=headers("user-b")).status_code == 200
    assert (
        client.put(f"/foods/{food_id}", json={"name": "No"}, headers=headers("user-b")).status_code
        == 403
    )


def test_admin_food_delete_cascades_cross_principal_diary_entries(security_context) -> None:
    client, session = security_context
    created = client.post(
        "/foods", json=food_payload("Globally used"), headers=headers("admin-a")
    ).json()
    for token, meal_type in (("admin-a", "breakfast"), ("user-b", "lunch")):
        diary = client.post(
            "/diary/entries",
            json={
                "food_id": created["id"],
                "entry_date": current_diary_date().isoformat(),
                "quantity": 1,
                "meal_type": meal_type,
            },
            headers=headers(token),
        )
        assert diary.status_code == 201, diary.text

    denied = client.delete(f"/foods/{created['id']}", headers=headers("user-b"))
    assert denied.status_code == 403

    deletion = client.delete(f"/foods/{created['id']}", headers=headers("admin-a"))
    assert deletion.status_code == 204
    assert deletion.content == b""
    assert client.get(f"/foods/{created['id']}", headers=headers("user-b")).status_code == 404
    assert session.exec(select(DiaryEntry).where(DiaryEntry.food_id == UUID(created["id"]))).all() == []
    assert client.delete(f"/foods/{created['id']}", headers=headers("admin-a")).status_code == 404
    for method, path in (
        ("GET", "/admin/foods"),
        ("GET", f"/admin/foods/{created['id']}"),
        ("DELETE", f"/admin/foods/{created['id']}"),
        ("POST", f"/admin/foods/{created['id']}/archive"),
        ("POST", f"/admin/foods/{created['id']}/restore"),
    ):
        assert client.request(method, path, headers=headers("admin-a")).status_code == 404


def test_future_diary_crud_without_if_match_preserves_replay_and_isolation(
    security_context,
) -> None:
    client, session = security_context
    food = client.post(
        "/foods", json=food_payload("Future diary food"), headers=headers("admin-a")
    ).json()
    entry_id = str(uuid4())
    payload = {
        "id": entry_id,
        "food_id": food["id"],
        "entry_date": (current_diary_date() + timedelta(days=30)).isoformat(),
        "quantity": 1,
        "meal_type": "breakfast",
    }

    rejected = client.post("/diary/entries", json=payload, headers=headers("user-b"))
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "DIARY_ENTRY_DATE_TOO_FAR"
    for offset in (0, 7, -3650):
        boundary = {**payload, "id": str(uuid4()),
                    "entry_date": (current_diary_date() + timedelta(days=offset)).isoformat()}
        result = client.post("/diary/entries", json=boundary, headers=headers("user-b"))
        assert result.status_code == 201, result.text
    beyond = {**payload, "entry_date": (current_diary_date() + timedelta(days=8)).isoformat()}
    assert client.post("/diary/entries", json=beyond, headers=headers("user-b")).status_code == 422
    payload["entry_date"] = (current_diary_date() + timedelta(days=7)).isoformat()
    created = client.post("/diary/entries", json=payload, headers=headers("user-b"))
    replayed = client.post("/diary/entries", json=payload, headers=headers("user-b"))
    assert created.status_code == replayed.status_code == 201
    assert created.json()["id"] == replayed.json()["id"] == entry_id
    assert created.json()["target_plan_id"] is None
    assert "target_provenance" not in created.json()

    # Existing far-future rows keep replay/update/delete behavior after the new limit.
    existing = session.get(DiaryEntry, UUID(entry_id))
    existing.entry_date = current_diary_date() + timedelta(days=30)
    session.add(existing)
    session.commit()
    payload["entry_date"] = existing.entry_date.isoformat()
    assert client.post("/diary/entries", json=payload, headers=headers("user-b")).status_code == 201
    assert (
        client.patch(
            f"/diary/entries/{entry_id}",
            json={"quantity": 2},
            headers=headers("admin-a"),
        ).status_code
        == 404
    )
    updated = client.patch(
        f"/diary/entries/{entry_id}",
        json={"quantity": 2},
        headers=headers("user-b"),
    )
    assert updated.status_code == 200
    assert updated.json()["quantity"] == 2
    assert client.delete(f"/diary/entries/{entry_id}", headers=headers("user-b")).status_code == 204


def test_legacy_completed_row_does_not_block_or_receive_diary_crud_writes(
    security_context,
) -> None:
    client, session = security_context
    food = client.post(
        "/foods", json=food_payload("Legacy status food"), headers=headers("admin-a")
    ).json()
    diary_date = current_diary_date().isoformat()
    session.exec(
        text(
            "CREATE TABLE diary_day_status "
            "(id TEXT PRIMARY KEY, principal_id TEXT, diary_date TEXT, status TEXT, "
            "version INTEGER, entry_count INTEGER, completed_at TEXT)"
        )
    )
    session.exec(
        text(
            "CREATE TABLE diary_day_status_history "
            "(id TEXT PRIMARY KEY, day_status_id TEXT, event_type TEXT)"
        )
    )
    status_id = str(uuid4())
    session.exec(
        text(
            "INSERT INTO diary_day_status "
            "(id,principal_id,diary_date,status,version,entry_count,completed_at) "
            "VALUES (:id,:principal_id,:diary_date,'complete',7,0,:completed_at)"
        ),
        params={
            "id": status_id,
            "principal_id": str(PRINCIPAL_B),
            "diary_date": diary_date,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    session.exec(
        text(
            "INSERT INTO diary_day_status_history (id,day_status_id,event_type) "
            "VALUES (:id,:day_status_id,'completed')"
        ),
        params={"id": str(uuid4()), "day_status_id": status_id},
    )
    session.commit()

    created = client.post(
        "/diary/entries",
        json={
            "food_id": food["id"],
            "entry_date": diary_date,
            "quantity": 1,
            "meal_type": "lunch",
        },
        headers=headers("user-b"),
    )
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]
    assert (
        client.patch(
            f"/diary/entries/{entry_id}",
            json={"quantity": 2},
            headers=headers("user-b"),
        ).status_code
        == 200
    )
    assert client.delete(f"/diary/entries/{entry_id}", headers=headers("user-b")).status_code == 204
    assert session.exec(text("SELECT count(*) FROM diary_day_status")).scalar_one() == 1
    assert session.exec(text("SELECT count(*) FROM diary_day_status_history")).scalar_one() == 1


def test_admin_monitoring_is_authorized_and_read_only(security_context) -> None:
    client, _ = security_context
    assert client.get("/admin/users", headers=headers("user-b")).status_code == 403
    assert client.get(f"/admin/users/{PRINCIPAL_B}", headers=headers("user-b")).status_code == 403
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
    ["detail", "diary", "diary_invalid"],
)
def test_admin_monitoring_gets_execute_no_dml(security_context, monkeypatch, endpoint: str) -> None:
    client, session = security_context
    current_response, plan_state = _seed_current_target_revisions(client, session)
    current_plan = current_response["plan"]
    today = current_diary_date()
    food = client.post(
        "/foods", json=food_payload("Monitoring food"), headers=headers("admin-a")
    ).json()
    session.add_all(
        [
            DiaryEntry(
                principal_id=PRINCIPAL_B,
                entry_date=today,
                food_id=UUID(food["id"]),
                quantity=1,
                recorded_unit_type=food["default_unit_type"],
                recorded_unit_amount=food["unit_amount"],
                recorded_unit_basis=food["unit_basis"],
            ),
            DiaryEntry(
                principal_id=PRINCIPAL_B,
                entry_date=today - timedelta(days=1),
                food_id=UUID(food["id"]),
                quantity=1,
                recorded_unit_type=food["default_unit_type"],
                recorded_unit_amount=food["unit_amount"],
                recorded_unit_basis=food["unit_basis"],
            ),
        ]
    )
    session.commit()
    paths = {
        "detail": f"/admin/users/{PRINCIPAL_B}",
        "diary": f"/admin/users/{PRINCIPAL_B}/diary?entry_date={today.isoformat()}",
        "diary_invalid": f"/admin/users/{PRINCIPAL_B}/diary?cursor=not-a-cursor",
    }
    path = paths[endpoint]
    engine, statements, cleanup = _install_admin_read_guards(monkeypatch, session)
    _reject_admin_commit(monkeypatch, session)
    try:
        response_documents = []
        for _ in range(2):
            response = client.get(path, headers=headers("admin-a"))
            expected_status = 422 if endpoint == "diary_invalid" else 200
            assert response.status_code == expected_status, response.text
            response_documents.append(response.json())
            if endpoint == "detail":
                assert response.json()["current_target"]["plan"]["id"] == current_plan["id"]
            elif endpoint == "diary":
                assert [item["entry_date"] for item in response.json()["items"]] == [
                    today.isoformat()
                ]
            elif endpoint == "diary_invalid":
                assert response.json()["detail"]["code"] == "INVALID_CURSOR"
            _assert_plans_unchanged(engine, plan_state)
        assert response_documents[0] == response_documents[1]
    finally:
        cleanup()

    normalized = [statement.lower() for statement in statements]
    assert not any(
        statement.startswith(("insert ", "update ", "delete ")) for statement in normalized
    )
    assert not any(" for update" in statement for statement in normalized)


def test_plan025_admin_diary_service_failure_executes_no_dml(security_context, monkeypatch) -> None:
    client, session = security_context
    _, plan_state = _seed_current_target_revisions(client, session)
    engine, statements, cleanup = _install_admin_read_guards(monkeypatch, session)
    _reject_admin_commit(monkeypatch, session)

    def fail_diary_page(*_args, **_kwargs):
        raise RuntimeError("synthetic admin diary failure")

    monkeypatch.setattr("app.api.routes.admin.admin_diary_page", fail_diary_page)
    try:
        with pytest.raises(RuntimeError, match="synthetic admin diary failure"):
            client.get(f"/admin/users/{PRINCIPAL_B}/diary", headers=headers("admin-a"))
        _assert_plans_unchanged(engine, plan_state)
    finally:
        cleanup()

    normalized = [statement.lower() for statement in statements]
    assert not any(
        statement.startswith(("insert ", "update ", "delete ")) for statement in normalized
    )
    assert not any(" for update" in statement for statement in normalized)


def test_client_authoritative_identity_and_role_are_rejected(security_context) -> None:
    client, _ = security_context
    for field in ("principal_id", "owner_id", "user_id", "role"):
        payload = profile_payload()
        payload[field] = "admin"
        payload["effective_from"] = current_diary_date().isoformat()
        assert (
            client.post("/profile/preview", json=payload, headers=headers("user-b")).status_code
            == 422
        )


def test_openapi_declares_http_bearer_security() -> None:
    app.openapi_schema = None
    schema = app.openapi()
    scheme = schema["components"]["securitySchemes"]["BearerAuth"]
    assert scheme["type"] == "http" and scheme["scheme"] == "bearer"
    assert schema["paths"]["/admin/users"]["get"]["security"] == [{"BearerAuth": []}]
    assert schema["paths"]["/foods"]["get"]["security"] == [{"BearerAuth": []}]


def test_malformed_legacy_token_returns_generic_401(
    security_context,
) -> None:
    client, _ = security_context
    encoded_header = base64.urlsafe_b64encode(
        json.dumps({"alg": [], "kid": "test"}).encode()
    ).rstrip(b"=")
    malformed_token = f"{encoded_header.decode()}.e30.c2ln"

    response = client.get("/foods", headers={"Authorization": "Bearer " + malformed_token})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIAL"
    assert response.json()["detail"].keys() == {"code", "message_ar"}


def test_production_auth_and_cors_configuration_fail_closed() -> None:
    validate_runtime_configuration(Settings(environment="production"))
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(allowed_origins=["*"])


@pytest.mark.parametrize("method,path", [
    ("get", "/labs/catalog"), ("get", "/labs"), ("get", "/labs/tests/hba1c"),
    ("post", "/labs/results"),
    ("patch", f"/labs/results/{PRINCIPAL_A}"),
    ("delete", f"/labs/results/{PRINCIPAL_A}"),
    ("get", f"/admin/users/{PRINCIPAL_B}/labs"),
    ("get", f"/admin/users/{PRINCIPAL_B}/labs/tests/hba1c"),
])
def test_labs_requires_bearer_and_never_caches_auth_errors(security_context, method, path):
    client, _ = security_context
    response = client.request(method, path)
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"
    assert "hba1c" not in response.text


@pytest.mark.parametrize("suffix", ["", "/tests/hba1c"])
def test_labs_admin_monitoring_rejects_normal_users(security_context, suffix):
    client, _ = security_context
    response = client.get(f"/admin/users/{PRINCIPAL_A}/labs{suffix}", headers=headers("user-b"))
    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("invalid_state", ["expired", "tampered"])
def test_expired_or_tampered_session_is_rejected(security_context, invalid_state):
    client, session = security_context
    token = _token("user-b")
    if invalid_state == "expired":
        row = session.exec(select(AuthSession).where(AuthSession.token_hash == token_digest(token))).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.add(row)
        session.commit()
    else:
        token = token[:-1] + ("A" if token[-1] != "A" else "B")
    response = client.get("/profile", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIAL"
    assert token not in response.text
