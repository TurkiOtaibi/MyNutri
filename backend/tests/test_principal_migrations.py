from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import Session

from app.core.auth import PrincipalContext
from app.schemas import ProfilePreview, TargetPlanActivationRequest
from app.services.profile import to_target_response
from app.services.target_plans import TargetPlanError, activate_plan

BASELINE_HASHES = {
    "0001_initial.py": "8a4a122abcdc3da143a472c4317a5789aa8ba96828cc0ad168ea8b776ed138e4",
    "0002_foods_v1_per_basis.py": "8a148572e2ac061fc7815b8fe4c4a73eb61fbb4c3b648fec68b035b42c7cdb3a",
    "0003_diary_meal_type.py": "3df7b5160cc393a7df1a5ef3765b318a228df23fc26908ec8ed338ac57168929",
}
DEPLOYMENT_PRINCIPAL = UUID("00000000-0000-0000-0000-000000000001")


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration rehearsals.")
    database = make_url(url).database or ""
    if not database.startswith("mynutri_test_"):
        pytest.fail("Migration tests refuse a database without the mynutri_test_ prefix.")
    return url


def _run_alembic(url: str, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "DATABASE_URL": url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env=environment,
        text=True,
        capture_output=True,
        check=check,
    )


def _reset_database(url: str) -> None:
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def _seed_0003(url: str) -> dict[str, UUID]:
    identifiers = {"profile": uuid4(), "food": uuid4(), "diary": uuid4()}
    snapshot = {
        "food_id": str(identifiers["food"]),
        "name": "Legacy fixture",
        "nutrition_basis": "per_100g",
        "default_unit_type": "serving",
        "unit_amount": 100,
        "unit_basis": "g",
        "calories": 100,
        "protein_g": 10,
        "carb_g": 20,
        "fat_g": 5,
        "log_mode": "servings",
    }
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO profile
                  (id, sex, birth_date, height_cm, weight_kg, activity_level, goal,
                   protein_per_kg, fat_pct, updated_at)
                VALUES
                  (:id, 'male', '1990-01-01', 175, 80, 'moderate', 'maintain', 1.2, 0.25, now())
                """
            ),
            {"id": identifiers["profile"]},
        )
        connection.execute(
            text(
                """
                INSERT INTO food
                  (id, name, nutrition_basis, default_unit_type, unit_amount, unit_basis,
                   calories, protein_g, carb_g, fat_g, created_at, updated_at)
                VALUES
                  (:id, 'Legacy fixture', 'per_100g', 'serving', 100, 'g',
                   100, 10, 20, 5, now(), now())
                """
            ),
            {"id": identifiers["food"]},
        )
        connection.execute(
            text(
                """
                INSERT INTO diary_entry
                  (id, entry_date, food_id, quantity, nutrition_snapshot, created_at, meal_type)
                VALUES
                  (:id, '2026-01-01', :food_id, 1, CAST(:snapshot AS jsonb), now(), 'breakfast')
                """
            ),
            {
                "id": identifiers["diary"],
                "food_id": identifiers["food"],
                "snapshot": json.dumps(snapshot, separators=(",", ":")),
            },
        )
    engine.dispose()
    return identifiers


@pytest.mark.migration
def test_immutable_baseline_revision_hashes() -> None:
    versions = Path(__file__).parents[1] / "alembic" / "versions"
    actual = {
        name: hashlib.sha256((versions / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in BASELINE_HASHES
    }
    assert actual == BASELINE_HASHES


@pytest.mark.migration
def test_fresh_postgresql_upgrade_has_one_head_and_wave1_food_contract() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")

    engine = create_engine(url)
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0010_target_plan_expand"
        )
    assert "principal" in inspector.get_table_names()
    for table in ("profile", "food", "diary_entry"):
        owner = next(
            column for column in inspector.get_columns(table) if column["name"] == "principal_id"
        )
        assert owner["nullable"] is False
    profile_uniques = {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("profile")
    }
    assert ("principal_id",) in profile_uniques
    food_columns = {column["name"]: column for column in inspector.get_columns("food")}
    for field in ("selenium_mcg", "iodine_mcg", "folate_dfe_mcg", "vitamin_a_rae_mcg"):
        assert food_columns[field]["nullable"] is True
        assert str(food_columns[field]["type"]) == "NUMERIC(10, 3)"
    assert {"food_group_contribution", "food_analytical_trait"}.issubset(
        inspector.get_table_names()
    )
    assert {
        "legacy_target_transition_snapshots", "target_plan", "idempotency_record"
    }.issubset(inspector.get_table_names())
    engine.dispose()


@pytest.mark.migration
def test_transition_snapshot_constraints_and_immutability() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")
    engine = create_engine(url)
    profile_id = uuid4()
    snapshot_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,status,created_at,updated_at) "
                "VALUES (:id,'active',now(),now())"
            ),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
    _run_alembic(url, "upgrade", "head")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO profile
                  (id,principal_id,sex,birth_date,height_cm,weight_kg,activity_level,goal,
                   protein_per_kg,fat_pct,cut_intensity,updated_at)
                VALUES
                  (:id,:principal,'male','1990-01-01',175,80,'moderate','maintain',
                   1.2,0.25,0.2,now())
                """
            ),
            {"id": profile_id, "principal": DEPLOYMENT_PRINCIPAL},
        )
        connection.execute(
            text(
                """
                INSERT INTO legacy_target_transition_snapshots
                  (id,principal_id,profile_id,transition_date,calendar_timezone,
                   target_document_schema_version,legacy_target_document,created_at)
                VALUES
                  (:id,:principal,:profile,'2026-07-16','Asia/Riyadh',1,
                   CAST(:document AS jsonb),now())
                """
            ),
            {
                "id": snapshot_id,
                "principal": DEPLOYMENT_PRINCIPAL,
                "profile": profile_id,
                "document": json.dumps(
                    {
                        "schema_version": 1,
                        "source": "legacy_unversioned_transition",
                        "captured_profile_inputs": {},
                        "resolved_targets": {},
                    }
                ),
            },
        )
    with engine.begin() as connection:
        with pytest.raises(DBAPIError, match="immutable"):
            connection.execute(
                text("UPDATE legacy_target_transition_snapshots SET transition_date='2026-07-17' WHERE id=:id"),
                {"id": snapshot_id},
            )
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT transition_date FROM legacy_target_transition_snapshots WHERE id=:id"),
            {"id": snapshot_id},
        ).scalar_one() == date(2026, 7, 16)
    downgrade = _run_alembic(url, "downgrade", "0008_food_groups_expand", check=False)
    assert downgrade.returncode != 0
    assert "Lossy" in downgrade.stderr
    engine.dispose()


@pytest.mark.migration
def test_populated_backfill_fails_closed_then_reconciles_without_history_change() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0003_diary_meal_type")
    identifiers = _seed_0003(url)
    engine = create_engine(url)
    with engine.connect() as connection:
        snapshot_before = connection.execute(
            text("SELECT nutrition_snapshot::text FROM diary_entry WHERE id = :id"),
            {"id": identifiers["diary"]},
        ).scalar_one()
    _run_alembic(url, "upgrade", "0004_principal_expand")

    absent = _run_alembic(url, "upgrade", "head", check=False)
    assert absent.returncode != 0
    assert "exactly one explicitly provisioned active Principal" in absent.stderr

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id, status, created_at, updated_at) VALUES (:id, 'active', now(), now())"
            ),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
    _run_alembic(url, "upgrade", "head")

    with engine.connect() as connection:
        for table in ("profile", "food", "diary_entry"):
            assert (
                connection.execute(
                    text(f"SELECT count(*) FROM {table} WHERE principal_id = :id"),
                    {"id": DEPLOYMENT_PRINCIPAL},
                ).scalar_one()
                == 1
            )
        snapshot_after = connection.execute(
            text("SELECT nutrition_snapshot::text FROM diary_entry WHERE id = :id"),
            {"id": identifiers["diary"]},
        ).scalar_one()
        assert snapshot_after == snapshot_before
        migrated_food = connection.execute(
            text(
                """
                SELECT primary_category_key, food_kind, group_data_status,
                       group_data_completeness, nutrition_source_type,
                       ingredients_text, nova_classification, nova_review_status,
                       selenium_mcg, iodine_mcg, folate_dfe_mcg, vitamin_a_rae_mcg
                  FROM food WHERE id = :id
                """
            ),
            {"id": identifiers["food"]},
        ).one()
        assert tuple(migrated_food) == (
            None,
            "unknown",
            "unknown",
            "unknown",
            "unknown",
            None,
            "unknown",
            "unreviewed",
            None,
            None,
            None,
            None,
        )
        assert (
            connection.execute(text("SELECT count(*) FROM food_group_contribution")).scalar_one()
            == 0
        )
        assert (
            connection.execute(text("SELECT count(*) FROM food_analytical_trait")).scalar_one() == 0
        )

        other_principal = uuid4()
        connection.execute(
            text(
                "INSERT INTO principal (id, status, created_at, updated_at) "
                "VALUES (:id, 'active', now(), now())"
            ),
            {"id": other_principal},
        )
        with pytest.raises(IntegrityError, match="fk_diary_entry_food_owner"):
            connection.execute(
                text("UPDATE diary_entry SET principal_id = :other WHERE id = :entry_id"),
                {"other": other_principal, "entry_id": identifiers["diary"]},
            )
    engine.dispose()


@pytest.mark.migration
def test_ambiguous_principal_backfill_is_rejected() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0003_diary_meal_type")
    _seed_0003(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")

    engine = create_engine(url)
    other_principal = uuid4()
    with engine.begin() as connection:
        for principal_id in (DEPLOYMENT_PRINCIPAL, other_principal):
            connection.execute(
                text(
                    "INSERT INTO principal (id, status, created_at, updated_at) "
                    "VALUES (:id, 'active', now(), now())"
                ),
                {"id": principal_id},
            )
    result = _run_alembic(url, "upgrade", "head", check=False)
    assert result.returncode != 0
    assert "exactly one explicitly provisioned active Principal" in result.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0004_principal_expand"
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM profile WHERE principal_id IS NOT NULL")
            ).scalar_one()
            == 0
        )
    engine.dispose()

    cleanup_engine = create_engine(url)
    with cleanup_engine.begin() as connection:
        connection.execute(text("DELETE FROM principal WHERE id = :id"), {"id": other_principal})
    cleanup_engine.dispose()
    _run_alembic(url, "upgrade", "head")


@pytest.mark.migration
def test_food_group_total_is_enforced_under_concurrent_transactions() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")
    engine = create_engine(url)
    food_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id, status, created_at, updated_at) "
                "VALUES (:id, 'active', now(), now())"
            ),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
    _run_alembic(url, "upgrade", "head")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO food
                  (id, principal_id, name, nutrition_basis, default_unit_type,
                   unit_amount, unit_basis, calories, protein_g, carb_g, fat_g,
                   group_data_status, group_data_completeness, created_at, updated_at)
                VALUES
                  (:id, :principal, 'Concurrent contributions', 'per_100g',
                   'serving', 100, 'g', 100, 10, 20, 5, 'known', 'partial', now(), now())
                """
            ),
            {"id": food_id, "principal": DEPLOYMENT_PRINCIPAL},
        )

    barrier = Barrier(2)

    def insert_contribution(group_key: str, amount: int) -> bool:
        connection = engine.connect()
        transaction = connection.begin()
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO food_group_contribution
                      (id, principal_id, food_id, group_key, amount_per_100_basis,
                       data_status, food_group_rules_version, created_at, updated_at)
                    VALUES
                      (:id, :principal, :food, :group_key, :amount, 'known',
                       '1.0.0', now(), now())
                    """
                ),
                {
                    "id": uuid4(),
                    "principal": DEPLOYMENT_PRINCIPAL,
                    "food": food_id,
                    "group_key": group_key,
                    "amount": amount,
                },
            )
            barrier.wait(timeout=10)
            transaction.commit()
            return True
        except IntegrityError:
            transaction.rollback()
            return False
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda item: insert_contribution(*item),
                (("fruits", 60), ("vegetables", 50)),
            )
        )

    assert sorted(results) == [False, True]
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT sum(amount_per_100_basis) "
                    "FROM food_group_contribution WHERE food_id = :food"
                ),
                {"food": food_id},
            ).scalar_one()
            <= 100
        )
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM food WHERE id = :food"), {"food": food_id})
    engine.dispose()


@pytest.mark.migration
def test_concurrent_first_legacy_activations_create_one_snapshot_and_plan() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")
    engine = create_engine(url)
    profile_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO principal (id,status,created_at,updated_at) VALUES (:id,'active',now(),now())"),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
    _run_alembic(url, "upgrade", "head")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO profile
                  (id,principal_id,sex,birth_date,height_cm,weight_kg,activity_level,goal,
                   protein_per_kg,fat_pct,cut_intensity,updated_at)
                VALUES
                  (:id,:principal,'male','1990-01-01',175,80,'moderate','maintain',
                   1.2,0.25,0.2,now())
                """
            ),
            {"id": profile_id, "principal": DEPLOYMENT_PRINCIPAL},
        )
    draft = ProfilePreview(
        sex="male", birth_date=date(1990, 1, 1), height_cm=175, weight_kg=82,
        activity_level="moderate", goal="maintain", protein_per_kg=1.2, fat_pct=0.25,
        selected_cut_intensity=0.2,
    )
    preview = to_target_response(draft)
    request = TargetPlanActivationRequest(
        **draft.model_dump(), confirmed=True, expected_preview_hash=preview.preview_hash
    )
    barrier = Barrier(2)

    def activate(key: str) -> str:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                activate_plan(
                    session, PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL), request, key
                )
                return "created"
            except TargetPlanError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(activate, ("race-a", "race-b")))
    assert results.count("created") == 1
    assert set(results) == {"created", "TARGET_PLAN_PENDING_EXISTS"}
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM legacy_target_transition_snapshots")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM target_plan")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM idempotency_record")).scalar_one() == 1
    engine.dispose()
