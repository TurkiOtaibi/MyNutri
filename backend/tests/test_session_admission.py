"""PostgreSQL admission reads, refresh throttling and writer revocation contracts."""

from datetime import timedelta

import pytest
from sqlalchemy import event, text, update
from sqlmodel import Session, select

from app.models import AuthSession, Principal, PrincipalRole, PrincipalStatus
from app.services import internal_auth as auth
from app.services.admin_lifecycle import (
    delete_account,
    reset_account_password,
    set_account_enabled,
)
from test_internal_auth import NOW, PASSWORD, account

pytestmark = pytest.mark.migration


def issued(engine):
    with Session(engine) as session:
        owner = account(session)
        result = auth.login(session, "example", PASSWORD, NOW)
        current = session.exec(select(AuthSession)).one()
        return owner.id, current.id, result.token


def test_recent_admissions_ignore_held_principal_and_session_locks(labs_postgresql_database):
    engine = labs_postgresql_database.engine
    owner_id, session_id, token = issued(engine)
    with Session(engine) as holder, Session(engine) as first, Session(engine) as second:
        holder.exec(select(Principal).where(Principal.id == owner_id).with_for_update()).one()
        holder.exec(select(AuthSession).where(AuthSession.id == session_id).with_for_update()).one()
        for reader in (first, second):
            reader.execute(text("SET LOCAL lock_timeout = '200ms'"))
            assert auth.admit_session(reader, token, NOW)[0].id == owner_id
        # Both read transactions remain open together; neither depends on the other.
        assert first.in_transaction() and second.in_transaction()


def test_refresh_only_after_five_minutes(labs_postgresql_database):
    engine = labs_postgresql_database.engine
    _, session_id, token = issued(engine)
    writes = []

    def observe(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("UPDATE"):
            writes.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        for seconds in (0, 299, 300, 301, 302, 600, 601, 602):
            with Session(engine) as session:
                auth.admit_session(session, token, NOW + timedelta(seconds=seconds))
        assert len(writes) == 2
        with Session(engine) as session:
            stored = session.get(AuthSession, session_id)
            assert stored.last_used_at == NOW + timedelta(seconds=602)
            assert stored.expires_at == NOW + timedelta(seconds=602, days=30)
    finally:
        event.remove(engine, "before_cursor_execute", observe)


def test_due_refresh_does_not_lock_principal(labs_postgresql_database):
    engine = labs_postgresql_database.engine
    owner_id, _, token = issued(engine)
    with Session(engine) as holder, Session(engine) as reader:
        holder.exec(select(Principal).where(Principal.id == owner_id).with_for_update()).one()
        reader.execute(text("SET LOCAL lock_timeout = '200ms'"))
        _, current = auth.admit_session(reader, token, NOW + timedelta(minutes=6))
        assert current.last_used_at == NOW + timedelta(minutes=6)


@pytest.mark.parametrize("invalid", ["revoked", "expired"])
def test_invalid_session_is_never_extended(labs_postgresql_database, invalid):
    engine = labs_postgresql_database.engine
    _, session_id, token = issued(engine)
    with Session(engine) as session:
        row = session.get(AuthSession, session_id)
        if invalid == "revoked":
            row.revoked_at = NOW
        else:
            row.expires_at = NOW
        session.add(row)
        session.commit()
        before = (row.last_used_at, row.expires_at)
        with pytest.raises(auth.AuthError, match="INVALID_CREDENTIAL"):
            auth.admit_session(session, token, NOW + timedelta(minutes=6))
        session.refresh(row)
        assert (row.last_used_at, row.expires_at) == before


@pytest.mark.parametrize("status", [s for s in PrincipalStatus if s != PrincipalStatus.active])
def test_non_active_admission_rejects_and_revokes(labs_postgresql_database, status):
    engine = labs_postgresql_database.engine
    owner_id, session_id, token = issued(engine)
    with Session(engine) as reader, Session(engine) as writer:
        auth.admit_session(reader, token, NOW)
        writer.execute(update(Principal).where(Principal.id == owner_id).values(status=status))
        writer.commit()
        with pytest.raises(auth.AuthError):
            auth.admit_session(reader, token, NOW)
        assert reader.get(AuthSession, session_id).revoked_at is not None


@pytest.mark.parametrize("action", ["change", "reset", "disable", "delete", "logout"])
def test_writer_revocation_is_visible_on_next_admission(labs_postgresql_database, action):
    engine = labs_postgresql_database.engine
    owner_id, session_id, token = issued(engine)
    with Session(engine) as reader, Session(engine) as writer:
        auth.admit_session(reader, token, NOW)
        admin = Principal(role=PrincipalRole.admin)
        writer.add(admin)
        writer.commit()
        if action == "change":
            other = auth.login(writer, "example", PASSWORD, NOW)
            _, current = auth.admit_session(writer, other.token, NOW)
            auth.change_password(writer, owner_id, current.id, PASSWORD, "changed-password", NOW)
        elif action == "reset":
            reset_account_password(writer, admin.id, owner_id, "changed-password", None, NOW)
        elif action == "disable":
            set_account_enabled(writer, admin.id, owner_id, False, NOW)
        elif action == "delete":
            delete_account(writer, admin.id, owner_id, None, NOW, 10)
        else:
            auth.logout(writer, owner_id, session_id, NOW)
        with pytest.raises(auth.AuthError):
            auth.admit_session(reader, token, NOW + timedelta(minutes=6))


@pytest.mark.parametrize("race", ["revoke", "expire", "refresh"])
def test_conditional_refresh_rechecks_concurrent_change(labs_postgresql_database, race):
    engine = labs_postgresql_database.engine
    _, session_id, token = issued(engine)
    refresh_time = NOW + timedelta(minutes=6)
    triggered = False

    def before_refresh(connection, cursor, statement, parameters, context, many):
        nonlocal triggered
        if triggered or not statement.lstrip().upper().startswith("UPDATE"):
            return
        triggered = True
        values = {"revoked_at": refresh_time} if race == "revoke" else (
            {"expires_at": refresh_time} if race == "expire" else
            {"last_used_at": refresh_time, "expires_at": refresh_time + timedelta(days=30)}
        )
        with Session(engine) as writer:
            writer.execute(update(AuthSession).where(AuthSession.id == session_id).values(**values))
            writer.commit()

    event.listen(engine, "before_cursor_execute", before_refresh)
    try:
        with Session(engine) as session:
            if race == "refresh":
                auth.admit_session(session, token, refresh_time)
            else:
                with pytest.raises(auth.AuthError, match="INVALID_CREDENTIAL"):
                    auth.admit_session(session, token, refresh_time)
        assert triggered
        with Session(engine) as session:
            row = session.get(AuthSession, session_id)
            assert row.last_used_at == (refresh_time if race == "refresh" else NOW)
            if race == "revoke":
                assert row.revoked_at == refresh_time
                assert row.expires_at == NOW + timedelta(days=30)
            elif race == "expire":
                assert row.expires_at == refresh_time
    finally:
        event.remove(engine, "before_cursor_execute", before_refresh)
