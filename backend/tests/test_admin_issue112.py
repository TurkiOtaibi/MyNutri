from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from app.models import Principal
from app.core.credentials import verify_password


@pytest.fixture
def admin_api(labs_client, lab_admin, as_actor, monkeypatch):
    as_actor(lab_admin)
    monkeypatch.setattr("app.api.routes.admin_accounts._background_reconcile_recent", lambda *args: None)
    return labs_client


def create(client, username="Test_User", key=None, **overrides):
    return client.post("/admin/accounts", headers={"Idempotency-Key": key or str(uuid4())}, json={
        "username": username, "display_name": "Synthetic User", "initial_password": "Initial-123", **overrides,
    })


def test_internal_creation_atomic_replay_and_duplicate(admin_api, labs_postgresql_session):
    key = str(uuid4())
    result = create(admin_api, key=key)
    assert result.status_code == 201, result.text
    body = result.json()
    row = labs_postgresql_session.get(Principal, UUID(body["principal_id"]))
    assert (row.username, row.normalized_username, row.email, row.auth_user_id) == ("Test_User", "test_user", None, None)
    assert row.role == "user" and row.status == "active" and row.must_change_password
    assert verify_password("Initial-123", row.password_hash)
    assert body["last_login_at"] is None and body["is_locked"] is False
    assert create(admin_api, key=key).json()["principal_id"] == body["principal_id"]
    assert create(admin_api, "test_user").status_code == 409
    assert create(admin_api, key=key, display_name="Different").status_code == 409
    assert create(admin_api, key=key, initial_password="Different-123").status_code == 409


@pytest.mark.parametrize("username,password", [("ab", "Initial-123"), ("عربي", "Initial-123"), ("a b", "Initial-123"), ("a" * 33, "Initial-123"), ("valid", "short")])
def test_create_rejects_invalid_credentials(admin_api, labs_postgresql_session, username, password):
    response = create(admin_api, username, initial_password=password)
    assert response.status_code == 422
    expected = "كلمة المرور قصيرة. استخدم 8 أحرف على الأقل." if password == "short" else "استخدم من 3 إلى 32 حرفًا لاسم المستخدم: أحرف إنجليزية أو أرقام أو . أو _ أو - فقط."
    assert response.json()["error"].get("message_ar") == expected
    assert labs_postgresql_session.exec(select(Principal).where(Principal.username == username)).first() is None


def test_username_list_search_lock_details_self(admin_api, labs_postgresql_session, lab_admin):
    first = create(admin_api, "alpha_one")
    assert first.status_code == 201
    assert create(admin_api, "alphaXone").status_code == 201
    row = labs_postgresql_session.get(Principal, UUID(first.json()["principal_id"]))
    row.locked_at = datetime.now(timezone.utc)
    row.last_login_at = datetime(2026, 10, 20, tzinfo=timezone.utc)
    labs_postgresql_session.add(row)
    labs_postgresql_session.commit()
    response = admin_api.get("/admin/accounts?search=ALPHA_&status=locked")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1 and body["items"][0]["username"] == "alpha_one"
    assert body["items"][0]["is_locked"] is True
    assert body["items"][0]["last_login_at"].startswith("2026-10-20")
    assert body["self"] is None
    assert admin_api.get("/admin/accounts").json()["self"]["principal_id"] == str(lab_admin.id)
    detail = admin_api.get(f"/admin/users/{row.id}").json()["account"]
    assert detail["username"] == "alpha_one" and detail["is_locked"] is True


def test_delete_requires_target_username_scrubs_and_reuses(admin_api, labs_postgresql_session):
    created = create(admin_api)
    assert created.status_code == 201
    principal_id = created.json()["principal_id"]
    path = f"/admin/accounts/{principal_id}"
    wrong = admin_api.request("DELETE", path, json={"confirm_email": "Test_User"})
    assert wrong.status_code == 422
    assert wrong.json()["error"]["message_ar"] == "اسم المستخدم المدخل لا يطابق هذا الحساب."
    deleted = admin_api.request("DELETE", path, json={"confirm_username": "test_USER"})
    assert deleted.status_code == 200
    row = labs_postgresql_session.get(Principal, UUID(principal_id))
    assert row.status == "deleted"
    assert all(getattr(row, field) is None for field in ("username", "normalized_username", "email", "display_name", "password_hash", "last_login_at"))
    replacement = create(admin_api)
    assert replacement.status_code == 201 and replacement.json()["principal_id"] != principal_id


def test_internal_create_is_admin_only(labs_client):
    assert create(labs_client).status_code == 403

@pytest.mark.parametrize("extra", [{"role": "admin"}, {"email": "legacy@example.test"}, {"username": "changed"}])
def test_internal_identity_and_role_cannot_be_changed(admin_api, extra):
    response = create(admin_api)
    assert response.status_code == 201
    path = "/admin/accounts/" + response.json()["principal_id"]
    assert admin_api.patch(path, json={"display_name": "Allowed", **extra}).status_code == 422


@pytest.mark.parametrize("operation", ["edit", "password", "status", "delete"])
def test_admin_cannot_mutate_self(admin_api, lab_admin, operation):
    path = f"/admin/accounts/{lab_admin.id}"
    if operation == "edit":
        response = admin_api.patch(path, json={"display_name": "Changed"})
    elif operation == "password":
        response = admin_api.put(path + "/password", json={"new_password": "Changed-123"})
    elif operation == "status":
        response = admin_api.put(path + "/status", json={"enabled": False})
    else:
        response = admin_api.request("DELETE", path, json={"confirm_username": "admin"})
    assert response.status_code == 403


def test_internal_delete_never_schedules_provider_reconciliation(admin_api, monkeypatch):
    calls = []
    monkeypatch.setattr("app.api.routes.admin_accounts._background_reconcile_recent", lambda *args: calls.append(args))
    result = create(admin_api)
    assert result.status_code == 201
    response = admin_api.request("DELETE", "/admin/accounts/" + result.json()["principal_id"], json={"confirm_username": "Test_User"})
    assert response.status_code == 200
    assert calls == []


def test_internal_create_requires_idempotency_key(admin_api):
    response = admin_api.post("/admin/accounts", json={"username": "valid", "display_name": "Valid", "initial_password": "Initial-123"})
    assert response.status_code == 422


def test_internal_create_transaction_rollback(labs_postgresql_session, lab_admin, monkeypatch):
    from sqlalchemy import event
    from app.services.admin_lifecycle import create_internal_account

    def reject_commit(session):
        session.flush()
        raise RuntimeError("synthetic transaction failure")

    event.listen(labs_postgresql_session, "before_commit", reject_commit)
    try:
        with pytest.raises(RuntimeError, match="synthetic transaction failure"):
            create_internal_account(labs_postgresql_session, lab_admin.id, "rollback", "Synthetic", "Initial-123", str(uuid4()), datetime.now(timezone.utc))
    finally:
        event.remove(labs_postgresql_session, "before_commit", reject_commit)
        labs_postgresql_session.rollback()
    assert labs_postgresql_session.exec(select(Principal).where(Principal.username == "rollback")).first() is None


def test_internal_reset_unlocks_revokes_and_preserves_username(admin_api, labs_postgresql_session, monkeypatch):
    from datetime import timedelta
    from app.models import AuthSession

    def provider_forbidden(*args, **kwargs):
        raise AssertionError("Internal lifecycle must not initialize the provider")

    monkeypatch.setattr("app.services.admin_auth._configured_admin_client", provider_forbidden)
    key = str(uuid4())
    result = create(admin_api, key=key)
    assert result.status_code == 201
    row = labs_postgresql_session.get(Principal, UUID(result.json()["principal_id"]))
    now = datetime.now(timezone.utc)
    row.locked_at = now
    row.failed_login_count = 5
    token = AuthSession(principal_id=row.id, token_hash="a" * 64, created_at=now, last_used_at=now, expires_at=now + timedelta(days=1))
    labs_postgresql_session.add(row)
    labs_postgresql_session.add(token)
    labs_postgresql_session.commit()
    response = admin_api.put(f"/admin/accounts/{row.id}/password", json={"new_password": "Reset-1234"})
    assert response.status_code == 204
    labs_postgresql_session.refresh(row)
    labs_postgresql_session.refresh(token)
    assert row.username == "Test_User" and row.locked_at is None and row.failed_login_count == 0
    assert not row.must_change_password and token.revoked_at is not None
    assert verify_password("Reset-1234", row.password_hash)
    assert create(admin_api, key=key).status_code == 409
    assert admin_api.request("DELETE", f"/admin/accounts/{row.id}", json={"confirm_username": "Test_User"}).status_code == 200
    assert labs_postgresql_session.exec(select(AuthSession).where(AuthSession.principal_id == row.id)).first() is None


def test_search_legacy_email_only_without_username(admin_api, labs_postgresql_session, lab_owner):
    legacy = labs_postgresql_session.get(Principal, lab_owner.id)
    legacy.email = "searchlegacy@example.test"
    labs_postgresql_session.add(legacy)
    result = create(admin_api)
    assert result.status_code == 201
    internal = labs_postgresql_session.get(Principal, UUID(result.json()["principal_id"]))
    internal.email = "searchinternal@example.test"
    labs_postgresql_session.add(internal)
    labs_postgresql_session.commit()
    assert admin_api.get("/admin/accounts?search=searchlegacy").json()["total"] == 1
    assert admin_api.get("/admin/accounts?search=searchinternal").json()["total"] == 0
    assert admin_api.get("/admin/accounts?search=%25").json()["total"] == 0


def test_internal_delete_failure_rolls_back_status_and_identity(admin_api, labs_postgresql_session, monkeypatch):
    from app.services.admin_lifecycle import delete_account

    created = create(admin_api)
    assert created.status_code == 201
    row = labs_postgresql_session.get(Principal, UUID(created.json()["principal_id"]))
    admin = labs_postgresql_session.exec(select(Principal).where(Principal.role == "admin")).one()
    def fail_purge(*args):
        raise RuntimeError("synthetic purge failure")
    monkeypatch.setattr("app.services.admin_lifecycle._purge_private_rows", fail_purge)
    with pytest.raises(RuntimeError, match="synthetic purge failure"):
        delete_account(labs_postgresql_session, admin.id, row.id, None, datetime.now(timezone.utc), 5, confirmation_username="Test_User")
    labs_postgresql_session.rollback()
    labs_postgresql_session.refresh(row)
    assert row.status == "active" and row.username == "Test_User" and row.password_hash is not None


def test_monitoring_search_uses_literal_username(admin_api):
    assert create(admin_api, "alpha_one").status_code == 201
    assert create(admin_api, "alphaXone").status_code == 201
    response = admin_api.get("/admin/users?search=ALPHA_")
    assert response.status_code == 200
    assert response.json()["total"] == 1
