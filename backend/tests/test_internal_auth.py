from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from app.core.credentials import hash_password
from app.models import AuthSession, Principal, PrincipalRole, PrincipalStatus
from app.services.internal_auth import AuthError, admit_session, login, logout, token_digest

NOW = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
PASSWORD = "synthetic-password"


def account(session, *, role=PrincipalRole.user, status=PrincipalStatus.active):
    row = Principal(
        username="Example",
        normalized_username="example",
        password_hash=hash_password(PASSWORD),
        role=role,
        status=status,
    )
    session.add(row)
    session.commit()
    return row


@pytest.mark.migration
def test_login_opaque_session_and_current_only_logout(labs_postgresql_database):
    with Session(labs_postgresql_database.engine) as session:
        row = account(session)
        first = login(session, "EXAMPLE", PASSWORD, NOW)
        second = login(session, "example", PASSWORD, NOW)
        assert first.token != second.token
        stored = session.exec(select(AuthSession)).all()
        assert all(item.token_hash not in (first.token, second.token) for item in stored)
        assert {item.token_hash for item in stored} == {
            token_digest(first.token),
            token_digest(second.token),
        }
        assert PASSWORD not in row.password_hash
        principal, active = admit_session(session, first.token, NOW)
        assert principal.id == row.id
        logout(session, row.id, active.id, NOW)
        with pytest.raises(AuthError):
            admit_session(session, first.token, NOW)
        admit_session(session, second.token, NOW)


@pytest.mark.migration
def test_unknown_and_wrong_password_same_response_and_same_hash_work(
    labs_postgresql_database, monkeypatch
):
    from app.services import internal_auth

    with Session(labs_postgresql_database.engine) as session:
        row = account(session)
        calls = []
        original = internal_auth.verify_password

        def spy(password, encoded):
            calls.append(encoded)
            return original(password, encoded)

        monkeypatch.setattr(internal_auth, "verify_password", spy)
        failures = []
        for username in ("unknown", "example"):
            with pytest.raises(AuthError) as failure:
                login(session, username, "incorrect", NOW)
            failures.append((failure.value.code, failure.value.message_ar))
        assert failures[0] == failures[1]
        assert len(calls) == 2
        assert calls[0] == internal_auth.DUMMY_PASSWORD_HASH
        assert session.exec(select(Principal)).all() == [row]
        assert row.failed_login_count == 1


@pytest.mark.migration
def test_user_lock_after_five_failures_never_auto_unlocks(labs_postgresql_database):
    with Session(labs_postgresql_database.engine) as session:
        row = account(session)
        for index in range(5):
            with pytest.raises(AuthError) as failure:
                login(session, "example", "incorrect", NOW)
            assert failure.value.code == ("USER_LOCKED" if index == 4 else "LOGIN_FAILED")
        assert row.failed_login_count == 5
        with pytest.raises(AuthError, match="USER_LOCKED"):
            login(session, "example", PASSWORD, NOW + timedelta(days=31))


@pytest.mark.migration
def test_admin_unlock_boundary_and_success_resets_counter(labs_postgresql_database):
    with Session(labs_postgresql_database.engine) as session:
        row = account(session, role=PrincipalRole.admin)
        for _ in range(5):
            with pytest.raises(AuthError):
                login(session, "example", "incorrect", NOW)
        with pytest.raises(AuthError, match="ADMIN_LOCKED"):
            login(session, "example", PASSWORD, NOW + timedelta(minutes=30, microseconds=-1))
        login(session, "example", PASSWORD, NOW + timedelta(minutes=30))
        assert row.failed_login_count == 0 and row.locked_at is None
        with pytest.raises(AuthError):
            login(session, "example", "incorrect", NOW + timedelta(minutes=31))
        login(session, "example", PASSWORD, NOW + timedelta(minutes=32))
        assert row.failed_login_count == 0


@pytest.mark.migration
@pytest.mark.parametrize(
    "status",
    [
        PrincipalStatus.disabled,
        PrincipalStatus.provisioning,
        PrincipalStatus.deleting,
        PrincipalStatus.deleted,
    ],
)
def test_non_active_accounts_cannot_login(labs_postgresql_database, status):
    with Session(labs_postgresql_database.engine) as session:
        account(session, status=status)
        with pytest.raises(AuthError) as failure:
            login(session, "example", PASSWORD, NOW)
        assert failure.value.code == (
            "ACCOUNT_DISABLED" if status == PrincipalStatus.disabled else "LOGIN_FAILED"
        )
        assert not session.exec(select(AuthSession)).all()


@pytest.mark.migration
def test_expiry_and_live_status_rechecked_on_every_admission(labs_postgresql_database):
    with Session(labs_postgresql_database.engine) as session:
        row = account(session)
        result = login(session, "example", PASSWORD, NOW)
        with pytest.raises(AuthError):
            admit_session(session, result.token, NOW + timedelta(days=30))
        result = login(session, "example", PASSWORD, NOW + timedelta(days=31))
        row.status = PrincipalStatus.disabled
        session.add(row)
        session.commit()
        with pytest.raises(AuthError, match="ACCOUNT_DISABLED"):
            admit_session(session, result.token, NOW + timedelta(days=31))
        assert all(item.revoked_at is not None for item in session.exec(select(AuthSession)).all())
        row.status = PrincipalStatus.active
        session.add(row)
        session.commit()
        renewed = login(session, "example", PASSWORD, NOW)
        admit_session(session, renewed.token, NOW + timedelta(days=29))
        _, active = admit_session(session, renewed.token, NOW + timedelta(days=31))
        assert active.expires_at == NOW + timedelta(days=61)


@pytest.mark.migration
def test_cli_create_reset_and_second_admin_refusal(labs_postgresql_database, monkeypatch, capsys):
    import io
    from app.ops import internal_admin
    from app.core.credentials import verify_password

    monkeypatch.setattr(internal_admin, "engine", labs_postgresql_database.engine)
    monkeypatch.setattr(
        "sys.argv", ["internal_admin", "create", "--username", "Administrator", "--password-stdin"]
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(PASSWORD + "\n"))
    internal_admin.main()
    assert PASSWORD not in capsys.readouterr().out
    from app.db.preflight import verify_database_compatibility
    from app.core.config import Settings

    verify_database_compatibility(
        labs_postgresql_database.engine,
        Settings(
            environment="production",
            database_url=labs_postgresql_database.url,
        ),
    )
    with Session(labs_postgresql_database.engine) as session:
        admin = session.exec(select(Principal)).one()
        assert admin.must_change_password
        with pytest.raises(ValueError, match="second Admin"):
            internal_admin.manage_admin(session, "create", "OtherAdmin", PASSWORD, NOW)
        issued = login(session, "Administrator", PASSWORD, NOW)
        admin.failed_login_count = 5
        admin.locked_at = NOW
        session.add(admin)
        session.commit()
    monkeypatch.setattr("sys.argv", ["internal_admin", "reset", "--username", "ADMINISTRATOR"])
    monkeypatch.setattr(internal_admin.getpass, "getpass", lambda _: "changed-synthetic-password")
    internal_admin.main()
    with Session(labs_postgresql_database.engine) as session:
        admin = session.exec(select(Principal)).one()
        assert verify_password("changed-synthetic-password", admin.password_hash)
        assert not admin.must_change_password
        assert admin.locked_at is None and admin.failed_login_count == 0
        with pytest.raises(AuthError):
            admit_session(session, issued.token, NOW)


@pytest.mark.migration
@pytest.mark.parametrize("password_stdin", [True, False])
def test_cli_attach_preserves_legacy_admin_and_sessions(
    labs_postgresql_database, monkeypatch, capsys, password_stdin
):
    import io
    from uuid import uuid4
    from app.ops import internal_admin
    from app.core.credentials import verify_password

    with Session(labs_postgresql_database.engine) as session:
        admin = Principal(
            role=PrincipalRole.admin,
            auth_user_id=uuid4(),
            email="legacy-admin@example.test",
            display_name="Legacy Admin",
            sessions_valid_after=NOW - timedelta(days=1),
        )
        session.add(admin)
        session.commit()
        existing = AuthSession(
            principal_id=admin.id,
            token_hash=token_digest("synthetic-existing-session"),
            created_at=NOW,
            last_used_at=NOW,
            expires_at=NOW + timedelta(days=30),
        )
        session.add(existing)
        session.commit()
        before = {
            key: getattr(admin, key)
            for key in Principal.model_fields
            if key not in {
                "username", "normalized_username", "password_hash",
                "must_change_password", "updated_at",
            }
        }
        existing_before = {key: getattr(existing, key) for key in AuthSession.model_fields}
    monkeypatch.setattr(internal_admin, "engine", labs_postgresql_database.engine)
    arguments = ["internal_admin", "attach", "--username", "Administrator"]
    if password_stdin:
        arguments.append("--password-stdin")
        monkeypatch.setattr("sys.stdin", io.StringIO(PASSWORD + "\n"))
    else:
        monkeypatch.setattr(internal_admin.getpass, "getpass", lambda _: PASSWORD)
    monkeypatch.setattr("sys.argv", arguments)
    internal_admin.main()
    captured = capsys.readouterr()
    assert PASSWORD not in captured.out + captured.err
    with Session(labs_postgresql_database.engine) as session:
        admin = session.exec(select(Principal)).one()
        assert {key: getattr(admin, key) for key in before} == before
        assert admin.username == "Administrator"
        assert admin.normalized_username == "administrator"
        assert verify_password(PASSWORD, admin.password_hash)
        assert not admin.must_change_password
        existing = session.exec(select(AuthSession)).one()
        assert {key: getattr(existing, key) for key in existing_before} == existing_before
        assert login(session, "ADMINISTRATOR", PASSWORD, NOW).principal.id == admin.id


@pytest.mark.migration
@pytest.mark.parametrize("status", [None, *[s for s in PrincipalStatus if s != PrincipalStatus.active]])
def test_attach_requires_existing_active_admin(labs_postgresql_database, status):
    from app.ops.internal_admin import manage_admin

    with Session(labs_postgresql_database.engine) as session:
        if status is not None:
            session.add(Principal(role=PrincipalRole.admin, status=status))
            session.commit()
        with pytest.raises(ValueError, match="active.*Admin"):
            manage_admin(session, "attach", "Administrator", PASSWORD, NOW)
        assert all(row.password_hash is None for row in session.exec(select(Principal)).all())


@pytest.mark.migration
def test_attach_refuses_existing_credentials(labs_postgresql_database):
    from app.ops.internal_admin import manage_admin

    with Session(labs_postgresql_database.engine) as session:
        admin = account(session, role=PrincipalRole.admin)
        before = {key: getattr(admin, key) for key in Principal.model_fields}
        with pytest.raises(ValueError, match="already.*credentials"):
            manage_admin(session, "attach", "Administrator", "replacement-password", NOW)
        session.refresh(admin)
        assert {key: getattr(admin, key) for key in before} == before


@pytest.mark.migration
@pytest.mark.parametrize(
    "username,password,message",
    [
        ("a b", PASSWORD, "3"),
        ("EXAMPLE", PASSWORD, "conflicts"),
        ("Administrator", "short", "8"),
    ],
    ids=["invalid-username", "taken-username", "invalid-password"],
)
def test_attach_rejects_invalid_or_taken_credentials(
    labs_postgresql_database, username, password, message
):
    from app.ops.internal_admin import manage_admin

    with Session(labs_postgresql_database.engine) as session:
        account(session)
        admin = Principal(role=PrincipalRole.admin)
        session.add(admin)
        session.commit()
        before = {key: getattr(admin, key) for key in Principal.model_fields}
        with pytest.raises(ValueError, match=message):
            manage_admin(session, "attach", username, password, NOW)
        session.refresh(admin)
        assert {key: getattr(admin, key) for key in before} == before


@pytest.mark.migration
def test_username_case_insensitive_database_uniqueness(labs_postgresql_database):
    from sqlalchemy.exc import IntegrityError

    with Session(labs_postgresql_database.engine) as session:
        account(session)
        session.add(
            Principal(
                username="EXAMPLE",
                normalized_username="example",
                password_hash=hash_password(PASSWORD),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        # A mismatched normalized identity cannot bypass the unique constraint.
        session.add(
            Principal(
                username="EXAMPLE",
                normalized_username="other",
                password_hash=hash_password(PASSWORD),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


@pytest.mark.migration
def test_admin_reset_unlocks_without_forced_change_and_revokes_all(labs_postgresql_database):
    from app.services.admin_lifecycle import reset_account_password, set_account_enabled
    from app.core.credentials import verify_password

    class NoProviderCalls:
        def reset_password(self, *args):
            raise AssertionError("Internal-only users must not call a provider")

    with Session(labs_postgresql_database.engine) as session:
        admin = Principal(role=PrincipalRole.admin)
        session.add(admin)
        row = account(session)
        first = login(session, "example", PASSWORD, NOW)
        second = login(session, "example", PASSWORD, NOW)
        row.locked_at = NOW
        row.failed_login_count = 5
        row.must_change_password = True
        session.add(row)
        session.commit()
        reset_account_password(
            session, admin.id, row.id, "changed-synthetic-password", NOW
        )
        assert not row.must_change_password
        assert row.locked_at is None and row.failed_login_count == 0
        assert verify_password("changed-synthetic-password", row.password_hash)
        for token in (first.token, second.token):
            with pytest.raises(AuthError):
                admit_session(session, token, NOW)
        current = login(session, "example", "changed-synthetic-password", NOW)
        set_account_enabled(session, admin.id, row.id, False, NOW)
        assert all(item.revoked_at is not None for item in session.exec(select(AuthSession)).all())
        with pytest.raises(AuthError):
            admit_session(session, current.token, NOW)


@pytest.mark.migration
def test_auth_http_forced_change_and_secret_safe_validation(labs_postgresql_database):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_session

    with Session(labs_postgresql_database.engine) as session:
        row = account(session)
        row.must_change_password = True
        session.add(row)
        session.commit()

    def sessions():
        with Session(labs_postgresql_database.engine) as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.post(
                "/auth/login", json={"username": "Example", "password": PASSWORD}
            )
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert "set-cookie" not in response.headers
            body = response.json()
            assert body["account"]["must_change_password"] is True
            headers = {"Authorization": "Bearer " + body["access_token"]}
            for path in (
                "/account/me",
                "/profile",
                "/diary/entries",
                "/foods",
                "/labs",
                "/admin/accounts",
            ):
                refused = client.get(path, headers=headers)
                assert refused.status_code == 403
                assert refused.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"
            assert client.post("/auth/logout", headers=headers).status_code == 204
            assert client.get("/account/me", headers=headers).status_code == 401
            for payload in (
                {"username": "Example", "password": [PASSWORD]},
                {"username": "Example", "password": PASSWORD, "extra": PASSWORD},
            ):
                invalid = client.post("/auth/login", json=payload)
                assert invalid.status_code == 422
                assert PASSWORD not in invalid.text
            invalid = client.post(
                "/auth/login",
                content='{"password":"' + PASSWORD,
                headers={"Content-Type": "application/json"},
            )
            assert invalid.status_code == 422 and PASSWORD not in invalid.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.migration
def test_migration_preserves_legacy_and_downgrades(labs_postgresql_database):
    from sqlalchemy import inspect, text
    from uuid import uuid4
    from labs_fixtures import run_labs_alembic

    run_labs_alembic("downgrade", "e9b7f5d01423")
    identity = uuid4()
    with labs_postgresql_database.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id, role, status, email, created_at, updated_at) VALUES (:id, 'user', 'active', 'legacy@example.test', now(), now())"
            ),
            {"id": identity},
        )
        connection.execute(
            text(
                "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon NOLOGIN; END IF; IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF; END $$"
            )
        )
        connection.execute(text("GRANT SELECT ON principal TO anon, authenticated"))
    run_labs_alembic("upgrade", "head")
    with Session(labs_postgresql_database.engine) as session:
        legacy = session.get(Principal, identity)
        assert legacy.email == "legacy@example.test"
        assert legacy.username is None and legacy.password_hash is None
        assert legacy.failed_login_count == 0 and not legacy.must_change_password
        account(session)
        login(session, "Example", PASSWORD, NOW)
    run_labs_alembic("check")
    sql = run_labs_alembic("upgrade", "e9b7f5d01423:head", "--sql")
    assert "CREATE TABLE auth_session" in sql.stdout
    with labs_postgresql_database.engine.connect() as connection:
        assert connection.scalar(
            text("SELECT relrowsecurity FROM pg_class WHERE oid='auth_session'::regclass")
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.role_table_grants WHERE table_name IN ('principal','auth_session') AND grantee='PUBLIC'"
                )
            )
            == 0
        )
        for role in ("anon", "authenticated"):
            for table in ("principal", "auth_session"):
                assert not connection.scalar(
                    text("SELECT has_table_privilege(:role, :table, 'SELECT')"),
                    {"role": role, "table": table},
                )
    run_labs_alembic("downgrade", "e9b7f5d01423")
    inspector = inspect(labs_postgresql_database.engine)
    assert "auth_session" not in inspector.get_table_names()
    assert "password_hash" not in {c["name"] for c in inspector.get_columns("principal")}
    with labs_postgresql_database.engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT email FROM principal WHERE id=:id"), {"id": identity})
            == "legacy@example.test"
        )
    run_labs_alembic("upgrade", "head")




@pytest.mark.migration
def test_linked_internal_reset_never_calls_provider(labs_postgresql_database):
    from uuid import uuid4
    from app.core.credentials import verify_password
    from app.services.admin_lifecycle import reset_account_password

    class FailedProvider:
        def reset_password(self, *args):
            raise AssertionError("Internal reset must never call a provider")

    with Session(labs_postgresql_database.engine) as session:
        admin = Principal(role=PrincipalRole.admin)
        session.add(admin)
        row = account(session)
        row.auth_user_id = uuid4()
        session.add(row)
        session.commit()
        issued = login(session, "example", PASSWORD, NOW)
        reset_account_password(
            session, admin.id, row.id, "replacement-password", NOW
        )
        assert verify_password("replacement-password", row.password_hash)
        with pytest.raises(AuthError):
            admit_session(session, issued.token, NOW)


@pytest.mark.migration
def test_internal_password_change_keeps_current_session_without_network(
    labs_postgresql_database, monkeypatch, caplog
):
    from uuid import uuid4
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_session

    def forbidden_provider(*args, **kwargs):
        raise AssertionError("Internal password operations must never initialize a provider")

    monkeypatch.setattr("httpx.HTTPTransport.handle_request", forbidden_provider)
    with Session(labs_postgresql_database.engine) as session:
        row = account(session)
        row.auth_user_id = uuid4()
        row.must_change_password = True
        session.add(row)
        session.commit()

    def sessions():
        with Session(labs_postgresql_database.engine) as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    try:
        with TestClient(app) as client:
            tokens = [
                client.post(
                    "/auth/login", json={"username": "example", "password": PASSWORD}
                ).json()["access_token"]
                for _ in range(2)
            ]
            headers = {"Authorization": "Bearer " + tokens[0]}
            wrong = client.post(
                "/auth/change-password",
                headers=headers,
                json={"current_password": "incorrect", "new_password": "replacement-password"},
            )
            assert wrong.status_code == 422
            assert wrong.json()["detail"]["message_ar"] == "كلمة المرور الحالية غير صحيحة."
            short = client.post(
                "/auth/change-password",
                headers=headers,
                json={"current_password": PASSWORD, "new_password": "short"},
            )
            assert short.status_code == 422
            assert (
                short.json()["detail"]["message_ar"]
                == "كلمة المرور قصيرة. استخدم 8 أحرف على الأقل."
            )
            changed = client.post(
                "/auth/change-password",
                headers=headers,
                json={"current_password": PASSWORD, "new_password": "replacement-password"},
            )
            assert changed.status_code == 200
            assert changed.json() == {"message_ar": "تم تغيير كلمة المرور."}
            assert changed.headers["cache-control"] == "no-store"
            current = client.get("/account/me", headers=headers)
            assert current.status_code == 200 and current.json()["must_change_password"] is False
            assert (
                client.get(
                    "/account/me", headers={"Authorization": "Bearer " + tokens[1]}
                ).status_code
                == 401
            )
            assert (
                client.post(
                    "/auth/login", json={"username": "example", "password": PASSWORD}
                ).status_code
                == 401
            )
            assert (
                client.post(
                    "/auth/login", json={"username": "example", "password": "replacement-password"}
                ).status_code
                == 200
            )
            logs = " ".join(record.getMessage() for record in caplog.records)
            assert all(secret not in logs for secret in [PASSWORD, "replacement-password", *tokens])
    finally:
        app.dependency_overrides.clear()




@pytest.mark.migration
def test_concurrent_login_failures_do_not_lose_increments(labs_postgresql_database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    with Session(labs_postgresql_database.engine) as session:
        row = account(session)
        identity = row.id
    start = Barrier(5)

    def fail():
        with Session(labs_postgresql_database.engine) as session:
            start.wait()
            with pytest.raises(AuthError) as error:
                login(session, "example", "incorrect", NOW)
            return error.value.code

    with ThreadPoolExecutor(max_workers=5) as pool:
        outcomes = list(pool.map(lambda _: fail(), range(5)))
    assert outcomes.count("LOGIN_FAILED") == 4
    assert outcomes.count("USER_LOCKED") == 1
    with Session(labs_postgresql_database.engine) as session:
        row = session.get(Principal, identity)
        assert row.failed_login_count == 5 and row.locked_at == NOW


@pytest.mark.migration
@pytest.mark.parametrize("operation", ["login", "change"])
def test_admin_reset_serializes_concurrent_internal_password_operations(
    labs_postgresql_database, monkeypatch, operation
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy.exc import OperationalError
    from app.services import admin_lifecycle
    from app.services.internal_auth import change_password

    entered, release, contender_started = Event(), Event(), Event()
    original_hash = admin_lifecycle.hash_password

    def paused_hash(password):
        entered.set()
        assert release.wait(10)
        return original_hash(password)

    monkeypatch.setattr(admin_lifecycle, "hash_password", paused_hash)
    with Session(labs_postgresql_database.engine) as session:
        admin = Principal(role=PrincipalRole.admin)
        session.add(admin)
        row = account(session)
        issued = login(session, "example", PASSWORD, NOW)
        _, current = admit_session(session, issued.token, NOW)
        admin_id, user_id, session_id = admin.id, row.id, current.id

    def reset():
        with Session(labs_postgresql_database.engine) as session:
            admin_lifecycle.reset_account_password(
                session, admin_id, user_id, "replacement-password", NOW
            )

    def contend():
        with Session(labs_postgresql_database.engine) as session:
            contender_started.set()
            with pytest.raises(AuthError):
                if operation == "login":
                    login(session, "example", PASSWORD, NOW)
                else:
                    change_password(
                        session, user_id, session_id, PASSWORD, "different-password", NOW
                    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        reset_task = pool.submit(reset)
        assert entered.wait(10)
        with Session(labs_postgresql_database.engine) as probe:
            with pytest.raises(OperationalError) as blocked:
                probe.exec(
                    select(Principal).where(Principal.id == user_id).with_for_update(nowait=True)
                ).one()
            assert blocked.value.orig.sqlstate == "55P03"
            probe.rollback()
        contender = pool.submit(contend)
        assert contender_started.wait(10)
        release.set()
        reset_task.result()
        contender.result()
    with Session(labs_postgresql_database.engine) as session:
        assert all(item.revoked_at is not None for item in session.exec(select(AuthSession)).all())
        login(session, "example", "replacement-password", NOW)
