"""Exercise the destructive cutover only against an opt-in disposable database."""

from datetime import date, datetime, timedelta, timezone
from functools import cache
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session

from app.models import (
    AuthSession, DiaryEntry, Food, IdempotencyRecord, LabResult, Principal,
    Profile, TargetPlan,
)
from app.core.credentials import hash_password
from labs_fixtures import reset_labs_database, run_labs_alembic, safe_labs_database_url


PARENT = "a1d9b7f23645"
REVISION = "b2e0c8f34756"
PRIVATE_TABLES = (
    "auth_session", "diary_entry", "lab_result", "idempotency_record",
    "target_plan", "profile",
)
TABLES = ("principal", "food", *PRIVATE_TABLES)
pytestmark = pytest.mark.migration


@cache
def _synthetic_password_hash():
    return hash_password("Synthetic-cutover-fixture-114!")


@pytest.fixture
def cutover_database():
    # Deliberately start at the parent: an empty head upgrade must fail its Admin guard.
    url = safe_labs_database_url()
    reset_labs_database()
    run_labs_alembic("upgrade", PARENT)
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()
        reset_labs_database()


def _actor(session, *, status="active", internal=False, role="user", retired=False):
    suffix = uuid4().hex[:12]
    now = datetime(2026, 10, 28, tzinfo=timezone.utc)
    principal = Principal(
        status=status, role=role, email=f"synthetic-{suffix}@example.test",
        display_name="Synthetic cutover fixture", auth_user_id=None if retired else uuid4(),
        retired_auth_user_id=uuid4() if retired else None,
        username=f"test_{suffix}" if internal else None,
        normalized_username=f"test_{suffix}" if internal else None,
        password_hash=_synthetic_password_hash() if internal else None,
        creation_idempotency_key=suffix, identity_requested_at=now,
        failed_login_count=2, locked_at=now, last_login_at=now,
        disabled_at=now if status == "disabled" else None,
    )
    session.add(principal)
    session.flush()
    profile = Profile(
        principal_id=principal.id, sex="female", birth_date=date(1990, 1, 1),
        height_cm=165, weight_kg=65, activity_level="light", goal="maintain",
    )
    food = Food(
        principal_id=principal.id, updated_by_principal_id=principal.id,
        name=f"Synthetic food {suffix}", normalized_name=f"synthetic food {suffix}",
        nutrition_basis="per_100g", default_unit_type="g", unit_amount=100,
        unit_basis="g", calories=100, protein_g=10, carb_g=10, fat_g=2,
    )
    session.add_all([profile, food])
    session.flush()
    plan = TargetPlan(
        principal_id=principal.id, profile_id=profile.id,
        effective_from=date(2026, 10, 28), revision=1,
        calculation_document={"target_result": {"calories": 1800}},
    )
    session.add(plan)
    session.flush()
    session.add_all([
        DiaryEntry(
            principal_id=principal.id, food_id=food.id, target_plan_id=plan.id,
            entry_date=date(2026, 10, 28), quantity=1, recorded_unit_type="g",
            recorded_unit_amount=100, recorded_unit_basis="g",
        ),
        LabResult(
            principal_id=principal.id, test_key="hba1c", test_date=date(2026, 10, 28),
            entered_value=5.2, entered_unit="%", note="Synthetic private note",
        ),
        IdempotencyRecord(
            principal_id=principal.id, operation="lab_results.create.v1",
            idempotency_key=suffix, request_hash="a" * 64, state="completed",
            response_status=201, response_document={"private": "synthetic"},
            completed_at=now,
        ),
        AuthSession(
            principal_id=principal.id, token_hash=uuid4().hex * 2,
            created_at=now, last_used_at=now, expires_at=now + timedelta(days=1),
        ),
    ])
    session.flush()
    return principal.id


def _seed(engine):
    with Session(engine) as session:
        retained = [
            _actor(session, internal=True, role="admin"),
            _actor(session, internal=True),
            _actor(session, internal=True, status="disabled"),
            _actor(session, status="deleted", retired=True),
        ]
        selected = [
            _actor(session, status=status, retired=status == "deleting")
            for status in ("active", "disabled", "provisioning", "deleting")
        ]
        session.commit()
    return selected, retained


def _snapshot(engine):
    with engine.connect() as connection:
        return {
            table: {
                row["id"]: dict(row)
                for row in connection.execute(text(f"SELECT * FROM {table}")).mappings()
            }
            for table in TABLES
        }


def _version(engine):
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _assert_cutover(before, after, selected, retained):
    assert after["food"] == before["food"]
    assert set(after["principal"]) == set(before["principal"])
    for principal_id in retained:
        assert after["principal"][principal_id] == before["principal"][principal_id]
    for principal_id in selected:
        row = after["principal"][principal_id]
        assert row["status"] == "deleted"
        assert row["role"] == "user"
        assert row["deleted_at"] is not None
        for field in (
            "auth_user_id", "retired_auth_user_id", "email", "display_name",
            "username", "normalized_username", "password_hash",
        ):
            assert row[field] is None
    for table in PRIVATE_TABLES:
        assert len(before[table]) == len(selected) + len(retained)
        assert after[table] == {
            key: row for key, row in before[table].items()
            if row["principal_id"] in retained
        }


def test_populated_cutover_purges_only_legacy_private_rows(cutover_database):
    inspector = inspect(cutover_database)
    principal_references = {
        (table, tuple(foreign_key["constrained_columns"]))
        for table in inspector.get_table_names()
        for foreign_key in inspector.get_foreign_keys(table)
        if foreign_key["referred_table"] == "principal"
    }
    assert principal_references == {
        *((table, ("principal_id",)) for table in PRIVATE_TABLES),
        ("food", ("created_by_principal_id",)),
        ("food", ("updated_by_principal_id",)),
    }
    selected, retained = _seed(cutover_database)
    before = _snapshot(cutover_database)
    run_labs_alembic("upgrade", REVISION)
    assert _version(cutover_database) == REVISION
    _assert_cutover(before, _snapshot(cutover_database), selected, retained)
    assert "No new upgrade operations detected" in run_labs_alembic("check").stdout


@pytest.mark.parametrize("admin_case", [
    "missing", "disabled", "legacy", "deleting", "deleted", "multiple",
])
def test_admin_guard_rolls_back_without_touching_any_rows(cutover_database, admin_case):
    with Session(cutover_database) as session:
        _actor(session)
        if admin_case != "missing":
            _actor(
                session, role="admin", internal=admin_case != "legacy",
                status=admin_case if admin_case in {"disabled", "deleting", "deleted"}
                else "active",
            )
        session.commit()
    if admin_case == "multiple":
        # Model a corrupted preflight state rather than relying only on the unique index.
        with cutover_database.begin() as connection:
            connection.execute(text("DROP INDEX uq_principal_single_admin"))
        with Session(cutover_database) as session:
            _actor(session, role="admin", internal=True)
            session.commit()
    before = _snapshot(cutover_database)
    result = run_labs_alembic("upgrade", REVISION, check=False)
    assert result.returncode != 0
    assert "LEGACY_CUTOVER" in result.stderr
    assert _version(cutover_database) == PARENT
    assert _snapshot(cutover_database) == before


def test_failure_during_purge_rolls_back_prior_deletions_and_status(cutover_database):
    _seed(cutover_database)
    with cutover_database.begin() as connection:
        connection.execute(text("""
            CREATE FUNCTION reject_cutover_profile_delete() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'SYNTHETIC_CUTOVER_FAILURE';
            END $$;
            CREATE TRIGGER reject_cutover_profile_delete BEFORE DELETE ON profile
            FOR EACH ROW EXECUTE FUNCTION reject_cutover_profile_delete();
        """))
    before = _snapshot(cutover_database)
    result = run_labs_alembic("upgrade", REVISION, check=False)
    assert result.returncode != 0
    assert "SYNTHETIC_CUTOVER_FAILURE" in result.stderr
    assert _version(cutover_database) == PARENT
    assert _snapshot(cutover_database) == before


def test_cutover_waits_for_principal_row_lock_before_purging(cutover_database):
    _, retained = _seed(cutover_database)
    before = _snapshot(cutover_database)
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    migration = ScriptDirectory.from_config(config).get_revision(REVISION).module
    # A current writer may have locked a Principal without issuing UPDATE yet.
    # The migration must drain that writer before taking private-table locks.
    with cutover_database.begin() as writer:
        writer.execute(text("SELECT id FROM principal WHERE id=:id FOR UPDATE"),
                       {"id": retained[0]})
        with pytest.raises(DBAPIError, match="lock timeout"):
            with cutover_database.begin() as migration_connection:
                migration_connection.execute(text("SET LOCAL lock_timeout = '100ms'"))
                with Operations.context(MigrationContext.configure(migration_connection)):
                    migration.upgrade()
    assert _snapshot(cutover_database) == before
    run_labs_alembic("upgrade", REVISION)
    assert _version(cutover_database) == REVISION


def test_downgrade_and_reexecution_never_restore_private_data(cutover_database):
    _seed(cutover_database)
    run_labs_alembic("upgrade", REVISION)
    after = _snapshot(cutover_database)
    run_labs_alembic("downgrade", PARENT)
    assert _snapshot(cutover_database) == after
    run_labs_alembic("upgrade", REVISION)
    assert _snapshot(cutover_database) == after


def test_offline_sql_executes_same_cutover_and_noop_downgrade(cutover_database):
    selected, retained = _seed(cutover_database)
    before = _snapshot(cutover_database)
    upgrade = run_labs_alembic("upgrade", f"{PARENT}:{REVISION}", "--sql").stdout
    with cutover_database.connect().execution_options(
        isolation_level="AUTOCOMMIT", no_parameters=True,
    ) as conn:
        conn.exec_driver_sql(upgrade)
    after = _snapshot(cutover_database)
    _assert_cutover(before, after, selected, retained)
    assert _version(cutover_database) == REVISION
    downgrade = run_labs_alembic("downgrade", f"{REVISION}:{PARENT}", "--sql").stdout
    with cutover_database.connect().execution_options(
        isolation_level="AUTOCOMMIT", no_parameters=True,
    ) as conn:
        conn.exec_driver_sql(downgrade)
    assert _version(cutover_database) == PARENT
    assert _snapshot(cutover_database) == after


def test_reexecution_emits_only_aggregate_counts(cutover_database):
    _seed(cutover_database)
    with Session(cutover_database) as session:
        empty_legacy = Principal(status="provisioning")
        session.add(empty_legacy)
        session.commit()
        empty_legacy_id = empty_legacy.id
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    migration = ScriptDirectory.from_config(config).get_revision(REVISION).module
    notices = []
    with cutover_database.begin() as connection:
        raw = connection.connection.driver_connection
        raw.add_notice_handler(lambda notice: notices.append(notice.message_primary))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            first = list(notices)
            notices.clear()
            migration.upgrade()
    expected_keys = ("accounts", *PRIVATE_TABLES, "tombstones")
    assert sorted(first) == sorted([
        "legacy_cutover accounts=5", "legacy_cutover tombstones=5",
        *(f"legacy_cutover {table}=4" for table in PRIVATE_TABLES),
    ])
    assert sorted(notices) == sorted(f"legacy_cutover {key}=0" for key in expected_keys)
    assert _snapshot(cutover_database)["principal"][empty_legacy_id]["status"] == "deleted"
