from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine

from app.models import Principal, PrincipalStatus

from labs_fixtures import run_labs_alembic


HEAD = "b6e4c2a78190"


def test_principal_model_has_retired_identity_and_lease_fields() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("principal")}
    assert {"identity_requested_at", "retired_auth_user_id"} <= columns
    assert "uq_principal_retired_auth_user_id" in {
        index["name"] for index in inspector.get_indexes("principal")
    }


def test_retired_identity_cannot_be_relinked_to_another_principal() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    retired_id = uuid4()
    with Session(engine) as session:
        session.add(Principal(status=PrincipalStatus.deleted, retired_auth_user_id=retired_id))
        session.commit()
        session.add(Principal(auth_user_id=retired_id))
        with pytest.raises(IntegrityError):
            session.commit()


def test_admin_lifecycle_revision_is_alembic_head() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    assert ScriptDirectory.from_config(config).get_heads() == [HEAD]


def test_admin_lifecycle_revision_is_single_head_with_principal_fields(
    labs_postgresql_database,
) -> None:
    inspector = inspect(labs_postgresql_database.engine)
    columns = {column["name"] for column in inspector.get_columns("principal")}
    assert {
        "creation_idempotency_key",
        "identity_requested_at",
        "retired_auth_user_id",
        "deletion_started_at",
        "deleted_at",
        "sessions_valid_after",
    } <= columns
    indexes = {index["name"] for index in inspector.get_indexes("principal")}
    assert {
        "uq_principal_single_admin",
        "uq_principal_creation_idempotency_key",
        "uq_principal_retired_auth_user_id",
    } <= indexes
    assert run_labs_alembic("heads").stdout.strip() == f"{HEAD} (head)"


@pytest.mark.migration
def test_populated_upgrade_preserves_existing_principal(labs_postgresql_database) -> None:
    run_labs_alembic("downgrade", "e8b7a42f6c31")
    identity = uuid4()
    with labs_postgresql_database.engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO principal (id, auth_user_id, email, role, status, created_at, updated_at)
            VALUES (:id, :auth_id, 'existing@example.test', 'user', 'active', now(), now())
        """), {"id": uuid4(), "auth_id": identity})
    run_labs_alembic("upgrade", "head")
    with labs_postgresql_database.engine.connect() as connection:
        row = connection.execute(text("""
            SELECT auth_user_id, status, retired_auth_user_id, sessions_valid_after
            FROM principal WHERE email='existing@example.test'
        """)).one()
        assert row == (identity, "active", None, None)


@pytest.mark.migration
def test_upgrade_refuses_multiple_admins_without_picking_one(labs_postgresql_database) -> None:
    run_labs_alembic("downgrade", "e8b7a42f6c31")
    with labs_postgresql_database.engine.begin() as connection:
        for index in range(2):
            connection.execute(text("""
                INSERT INTO principal (id, auth_user_id, email, role, status, created_at, updated_at)
                VALUES (:id, :auth_id, :email, 'admin', 'active', now(), now())
            """), {"id": uuid4(), "auth_id": uuid4(), "email": f"admin{index}@example.test"})
    result = run_labs_alembic("upgrade", "head", check=False)
    assert result.returncode != 0
    assert "ADMIN_LIFECYCLE_MULTIPLE_ADMINS" in result.stderr
    with labs_postgresql_database.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "e8b7a42f6c31"
        assert connection.scalar(text("SELECT count(*) FROM principal WHERE role='admin'")) == 2


@pytest.mark.migration
@pytest.mark.parametrize("blocked_by", ["provisioning", "deleting", "deleted", "cutoff"])
def test_downgrade_refuses_lifecycle_state_or_session_cutoff(
    labs_postgresql_database, blocked_by: str
) -> None:
    with labs_postgresql_database.engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO principal
              (id, auth_user_id, email, role, status, created_at, updated_at, sessions_valid_after)
            VALUES (:id, :auth_id, :email, 'user', :status, now(), now(), :cutoff)
        """), {
            "id": uuid4(), "auth_id": uuid4(), "email": f"{blocked_by}@example.test",
            "status": "active" if blocked_by == "cutoff" else blocked_by,
            "cutoff": "2026-09-28T00:00:01+00:00" if blocked_by == "cutoff" else None,
        })
    result = run_labs_alembic("downgrade", "e8b7a42f6c31", check=False)
    assert result.returncode != 0
    assert "ADMIN_LIFECYCLE_DOWNGRADE_BLOCKED" in result.stderr
    with labs_postgresql_database.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == HEAD
