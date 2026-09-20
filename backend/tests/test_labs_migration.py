from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect, null, text

from app import models
from app.models import IdempotencyRecord, IdempotencyState, TargetPlan
from labs_fixtures import run_labs_alembic, safe_labs_database_url

pytestmark = pytest.mark.migration
BASE = "d9f64a1c3e58"
HEAD = "e8b7a42f6c31"


def test_labs_migration_installs_exact_schema_and_clean_model(labs_postgresql_database):
    inspector = inspect(labs_postgresql_database.engine)
    assert "lab_result" in inspector.get_table_names()
    columns = {item["name"]: item for item in inspector.get_columns("lab_result")}
    assert set(columns) == {
        "id",
        "principal_id",
        "test_key",
        "test_date",
        "entered_value",
        "entered_unit",
        "created_at",
        "updated_at",
    }
    assert all(not item["nullable"] for item in columns.values())
    assert str(columns["entered_value"]["type"]) == "NUMERIC"
    assert str(columns["test_date"]["type"]) == "DATE"
    assert columns["test_key"]["type"].length == columns["entered_unit"]["type"].length == 64
    assert columns["created_at"]["type"].timezone and columns["updated_at"]["type"].timezone
    assert inspector.get_unique_constraints("lab_result")[0]["column_names"] == [
        "principal_id",
        "test_key",
        "test_date",
    ]
    fk = inspector.get_foreign_keys("lab_result")
    assert len(fk) == 1 and fk[0]["referred_table"] == "principal"
    assert fk[0]["options"]["ondelete"] == "RESTRICT"
    assert {item["name"] for item in inspector.get_indexes("lab_result")} == {
        "uq_lab_result_principal_test_date"
    }
    assert {item["name"] for item in inspector.get_check_constraints("lab_result")} == {
        "ck_lab_result_value_finite_nonnegative",
        "ck_lab_result_value_length",
        "ck_lab_result_test_key_nonempty",
        "ck_lab_result_entered_unit_nonempty",
    }
    assert "ix_idempotency_expiry" in {
        item["name"] for item in inspector.get_indexes("idempotency_record")
    }
    assert {item["name"] for item in inspector.get_check_constraints("idempotency_record")} >= {
        "ck_idempotency_completion",
        "ck_idempotency_state",
        "ck_idempotency_operation_expiry",
    }
    assert run_labs_alembic("heads").stdout.strip() == f"{HEAD} (head)"
    assert "No new upgrade operations detected" in run_labs_alembic("check").stdout


def test_populated_existing_data_and_expiry_survive_upgrade(
    labs_postgresql_database, lab_owner, labs_postgresql_session
):
    session = labs_postgresql_session
    profile_id = session.exec(
        text("SELECT id FROM profile WHERE principal_id=:id").bindparams(id=lab_owner.id)
    ).scalar_one()
    now = datetime(2026, 9, 20, tzinfo=timezone.utc)
    plan = TargetPlan(
        principal_id=lab_owner.id,
        profile_id=profile_id,
        effective_from=date(2026, 9, 20),
        revision=1,
        calculation_document={"target_result": {"calories": 1800}},
    )
    receipt = IdempotencyRecord(
        principal_id=lab_owner.id,
        operation="target_plan.write",
        idempotency_key="existing-plan",
        request_hash="a" * 64,
        state=IdempotencyState.completed,
        response_status=200,
        response_document={"retained": "exact replay"},
        completed_at=now,
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    food = models.Food(
        principal_id=lab_owner.id,
        name="Synthetic migration food",
        normalized_name="synthetic migration food",
        nutrition_basis=models.NutritionBasis.per_100g,
        default_unit_type=models.DefaultUnitType.g,
        unit_amount=1,
        unit_basis=models.UnitBasis.g,
        calories=100,
        protein_g=1,
        carb_g=2,
        fat_g=3,
    )
    session.add_all([plan, receipt, food])
    session.flush()
    session.add(
        models.DiaryEntry(
            principal_id=lab_owner.id,
            food_id=food.id,
            entry_date=date(2026, 9, 19),
            quantity=1,
            recorded_unit_type=models.DefaultUnitType.g,
            recorded_unit_amount=1,
            recorded_unit_basis=models.UnitBasis.g,
        )
    )
    session.commit()
    session.close()
    run_labs_alembic("downgrade", BASE)
    with labs_postgresql_database.engine.connect() as connection:
        before = {
            name: connection.execute(text(f"SELECT row_to_json(t) FROM {name} t ORDER BY id"))
            .scalars()
            .all()
            for name in (
                "principal",
                "profile",
                "target_plan",
                "idempotency_record",
                "food",
                "diary_entry",
            )
        }
    run_labs_alembic("upgrade", HEAD)
    with labs_postgresql_database.engine.connect() as connection:
        after = {
            name: connection.execute(text(f"SELECT row_to_json(t) FROM {name} t ORDER BY id"))
            .scalars()
            .all()
            for name in before
        }
    assert after == before


@pytest.mark.parametrize("kind", ["result", "in_progress_receipt", "completed_receipt"])
def test_downgrade_refuses_any_labs_data_without_deletion(
    labs_postgresql_database, labs_postgresql_session, lab_owner, kind
):
    session = labs_postgresql_session
    if kind == "result":
        session.add(
            models.LabResult(
                principal_id=lab_owner.id,
                test_key="hba1c",
                test_date=date(2026, 9, 19),
                entered_value=Decimal("5.270"),
                entered_unit="%",
            )
        )
    else:
        completed = kind == "completed_receipt"
        session.add(
            IdempotencyRecord(
                principal_id=lab_owner.id,
                operation="lab_results.create.v1",
                idempotency_key=str(uuid4()),
                request_hash="a" * 64,
                state=IdempotencyState.completed if completed else IdempotencyState.in_progress,
                expires_at=None,
                response_status=201 if completed else None,
                response_document={"receipt_version": 1, "result_ids": [str(uuid4())]}
                if completed
                else null(),
                completed_at=datetime.now(timezone.utc) if completed else None,
            )
        )
    session.commit()
    session.close()
    rejected = run_labs_alembic("downgrade", BASE, check=False)
    assert rejected.returncode != 0
    assert "LABS_V1_DOWNGRADE_BLOCKED" in rejected.stdout + rejected.stderr
    with labs_postgresql_database.engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        )
        assert (
            connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM lab_result)+(SELECT count(*) FROM idempotency_record WHERE operation='lab_results.create.v1')"
                )
            ).scalar_one()
            == 1
        )


def test_empty_downgrade_restores_not_null_and_can_upgrade_again(labs_postgresql_database):
    run_labs_alembic("downgrade", BASE)
    inspector = inspect(labs_postgresql_database.engine)
    assert "lab_result" not in inspector.get_table_names()
    assert (
        next(
            item
            for item in inspector.get_columns("idempotency_record")
            if item["name"] == "expires_at"
        )["nullable"]
        is False
    )
    assert "ck_idempotency_operation_expiry" not in {
        item["name"] for item in inspector.get_check_constraints("idempotency_record")
    }
    run_labs_alembic("upgrade", HEAD)


def test_private_grants_preserve_backend_and_unrelated_tables(labs_postgresql_database):
    engine = labs_postgresql_database.engine
    run_labs_alembic("downgrade", BASE)
    created = []
    safe_labs_database_url()
    try:
        with engine.begin() as connection:
            for role in ("anon", "authenticated"):
                if not connection.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
                ).scalar():
                    connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
                    created.append(role)
            # A permissive future-table default proves that the migration revokes grants.
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM pg_default_acl WHERE defaclnamespace='public'::regnamespace"
                    )
                ).scalar_one()
                == 0
            )
            connection.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO PUBLIC, anon, authenticated"
                )
            )
            connection.execute(text("GRANT SELECT ON food TO anon, authenticated"))
            before = connection.execute(
                text(
                    "SELECT relname, relacl::text FROM pg_class WHERE relnamespace='public'::regnamespace ORDER BY relname"
                )
            ).all()
        run_labs_alembic("upgrade", HEAD)
        with engine.connect() as connection:
            after = connection.execute(
                text(
                    "SELECT relname, relacl::text FROM pg_class WHERE relnamespace='public'::regnamespace AND relname NOT IN ('lab_result','lab_result_pkey','uq_lab_result_principal_test_date') ORDER BY relname"
                )
            ).all()
            assert after == before
            assert connection.execute(
                text(
                    "SELECT has_table_privilege(current_user,'lab_result','SELECT,INSERT,UPDATE,DELETE')"
                )
            ).scalar_one()
            for role in ("anon", "authenticated"):
                for privilege in (
                    "SELECT",
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                    "TRUNCATE",
                    "REFERENCES",
                    "TRIGGER",
                ):
                    assert not connection.execute(
                        text("SELECT has_table_privilege(:role,'lab_result',:privilege)"),
                        {"role": role, "privilege": privilege},
                    ).scalar_one()
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM pg_class c, LATERAL aclexplode(COALESCE(c.relacl,acldefault('r',c.relowner))) a WHERE c.oid='lab_result'::regclass AND a.grantee=0"
                    )
                ).scalar_one()
                == 0
            )
    finally:
        safe_labs_database_url()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated"
                )
            )
            connection.execute(text("REVOKE SELECT ON food FROM anon, authenticated"))
            for role in created:
                connection.execute(text(f'DROP ROLE "{role}"'))


def test_offline_upgrade_sql_and_downgrade_refusal():
    sql = run_labs_alembic("upgrade", f"{BASE}:{HEAD}", "--sql").stdout
    assert "CREATE TABLE lab_result" in sql
    assert "entered_value NUMERIC NOT NULL" in sql
    assert "DROP NOT NULL" in sql
    assert "REVOKE ALL PRIVILEGES" in sql
    rejected = run_labs_alembic("downgrade", f"{HEAD}:{BASE}", "--sql", check=False)
    assert rejected.returncode != 0
    assert "online empty-table preflight" in rejected.stdout + rejected.stderr
