from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from psycopg.errors import CheckViolation, NumericValueOutOfRange
from sqlalchemy import Numeric, String, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import Session

from app.core.auth import PrincipalContext
from app.models import (
    FOOD_GROUP_NUMERIC_COLUMNS,
    FOOD_NUMERIC_COLUMNS,
    DefaultUnitType,
    Food,
    FoodGroupContribution,
    NutritionBasis,
    Principal,
    UnitBasis,
)
from app.schemas import ProfilePreview, TargetPlanActivationRequest
from app.services.profile import to_target_response
from app.services.target_plans import TargetPlanError, activate_plan

BASELINE_HASHES = {
    "0001_initial.py": "8a4a122abcdc3da143a472c4317a5789aa8ba96828cc0ad168ea8b776ed138e4",
    "0002_foods_v1_per_basis.py": "8a148572e2ac061fc7815b8fe4c4a73eb61fbb4c3b648fec68b035b42c7cdb3a",
    "0003_diary_meal_type.py": "3df7b5160cc393a7df1a5ef3765b318a228df23fc26908ec8ed338ac57168929",
}
DEPLOYMENT_PRINCIPAL = UUID("00000000-0000-0000-0000-000000000001")
PLAN009_TIMESTAMP = datetime(2026, 7, 28, tzinfo=UTC)
PLAN009_GROUP_NAN_CONSTRAINTS = frozenset(
    {
        "ck_food_group_contribution_amount",
        "ck_food_group_contribution_amount_finite",
    }
)
PLAN012_V2_FIELDS = (
    "food_category_key",
    "grain_type",
    "baked_good_type",
    "grain_starch_type",
    "taxonomy_review_required",
)
PLAN012_LEGACY_CATEGORY_KEYS = (
    "vegetables",
    "fruits",
    "legumes",
    "whole_grains",
    "refined_grains",
    "nuts_seeds",
    "seafood",
    "dairy_fortified_alternatives",
    "eggs",
    "poultry",
    "red_meat",
    "processed_meat",
    "added_oils_fats",
    "sweets",
    "sugar_sweetened_beverages",
    "unsweetened_beverages",
    "herbs_spices",
    "mixed_dish",
    "other",
    None,
)
PLAN012_SAFE_LEGACY_CATEGORY_KEYS = tuple(
    key for key in PLAN012_LEGACY_CATEGORY_KEYS if key is not None
)


def _plan012_expected_tuple(
    legacy_primary_category_key: str | None,
) -> tuple[str, str | None, None, str | None, bool]:
    if legacy_primary_category_key == "whole_grains":
        return ("grains_starches", "whole", None, "other", True)
    if legacy_primary_category_key == "refined_grains":
        return ("grains_starches", "refined", None, "other", True)
    if legacy_primary_category_key is None:
        return ("other", None, None, None, True)
    return (legacy_primary_category_key, None, None, None, False)


@pytest.mark.migration
@pytest.mark.parametrize("legacy_primary_category_key", PLAN012_LEGACY_CATEGORY_KEYS)
def test_plan012_deterministic_0014_mapping_fixture_covers_every_v2_field(
    legacy_primary_category_key: str | None,
) -> None:
    expected = _plan012_expected_tuple(legacy_primary_category_key)

    assert len(expected) == len(PLAN012_V2_FIELDS)
    assert dict(zip(PLAN012_V2_FIELDS, expected, strict=True)) == {
        "food_category_key": expected[0],
        "grain_type": expected[1],
        "baked_good_type": expected[2],
        "grain_starch_type": expected[3],
        "taxonomy_review_required": expected[4],
    }


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
            "5294eff9a956"
        )
    assert "principal" in inspector.get_table_names()
    for table in ("profile", "diary_entry"):
        owner = next(
            column for column in inspector.get_columns(table) if column["name"] == "principal_id"
        )
        assert owner["nullable"] is False
    profile_uniques = {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("profile")
    }
    assert ("principal_id",) in profile_uniques
    food_columns = {column["name"]: column for column in inspector.get_columns("food")}
    assert "principal_id" not in food_columns
    assert food_columns["created_by_principal_id"]["nullable"] is False
    assert "category" not in food_columns
    assert food_columns["food_category_key"]["nullable"] is False
    for field in ("selenium_mcg", "iodine_mcg", "folate_dfe_mcg", "vitamin_a_rae_mcg"):
        assert food_columns[field]["nullable"] is True
        assert str(food_columns[field]["type"]) == "NUMERIC(10, 3)"
    assert {"food_group_contribution", "food_analytical_trait"}.issubset(
        inspector.get_table_names()
    )
    assert {
        "legacy_target_transition_snapshots", "target_plan", "idempotency_record"
    }.issubset(inspector.get_table_names())
    diary_columns = {column["name"]: column for column in inspector.get_columns("diary_entry")}
    assert diary_columns["target_plan_id"]["nullable"] is True
    assert diary_columns["snapshot_schema_version"]["nullable"] is True
    assert diary_columns["target_provenance"]["nullable"] is False
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
        owner_columns = {
            "profile": "principal_id",
            "food": "created_by_principal_id",
            "diary_entry": "principal_id",
        }
        for table, owner_column in owner_columns.items():
            assert (
                connection.execute(
                    text(f"SELECT count(*) FROM {table} WHERE {owner_column} = :id"),
                    {"id": DEPLOYMENT_PRINCIPAL},
                ).scalar_one()
                == 1
            )
        snapshot_after = connection.execute(
            text("SELECT nutrition_snapshot::text FROM diary_entry WHERE id = :id"),
            {"id": identifiers["diary"]},
        ).scalar_one()
        assert snapshot_after == snapshot_before
        migrated_diary = connection.execute(
            text(
                "SELECT target_plan_id, target_provenance, snapshot_schema_version "
                "FROM diary_entry WHERE id = :id"
            ),
            {"id": identifiers["diary"]},
        ).one()
        assert tuple(migrated_diary) == (None, "legacy_unversioned", None)
        migrated_food = connection.execute(
            text(
                """
                SELECT food_category_key, grain_type, taxonomy_review_required,
                       food_kind, group_data_status,
                       group_data_completeness, nutrition_source_type,
                       ingredients_text, nova_classification, nova_review_status,
                       selenium_mcg, iodine_mcg, folate_dfe_mcg, vitamin_a_rae_mcg
                  FROM food WHERE id = :id
                """
            ),
            {"id": identifiers["food"]},
        ).one()
        assert tuple(migrated_food) == (
            "other",
            None,
            True,
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
        with pytest.raises(IntegrityError, match="immutable|fk_diary_entry_food_owner"):
            connection.execute(
                text("UPDATE diary_entry SET principal_id = :other WHERE id = :entry_id"),
                {"other": other_principal, "entry_id": identifiers["diary"]},
            )
    engine.dispose()


@pytest.mark.migration
def test_snapshot_v2_database_shape_is_immutable_and_blocks_lossy_downgrade() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")
    engine = create_engine(url)
    entry_id = uuid4()
    food_id = uuid4()
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
                INSERT INTO food
                  (id,created_by_principal_id,name,normalized_name,food_category_key,
                   nutrition_basis,default_unit_type,unit_amount,unit_basis,
                   calories,protein_g,carb_g,fat_g,created_at,updated_at)
                VALUES
                  (:id,:principal,'Snapshot source','snapshot source','other','per_100g','serving',100,'g',
                   100,1,2,3,now(),now())
                """
            ),
            {"id": food_id, "principal": DEPLOYMENT_PRINCIPAL},
        )
        connection.execute(
            text(
                """
                INSERT INTO diary_entry
                  (id,principal_id,entry_date,food_id,quantity,meal_type,nutrition_snapshot,
                   target_plan_id,target_provenance,snapshot_schema_version,created_at)
                VALUES
                  (:id,:principal,'2026-07-16',:food,1,'breakfast',
                   CAST(:document AS jsonb),NULL,'legacy_unversioned',2,now())
                """
            ),
            {
                "id": entry_id,
                "principal": DEPLOYMENT_PRINCIPAL,
                "food": food_id,
                "document": json.dumps({"schema_version": 2}),
            },
        )
        connection.execute(
            text("UPDATE diary_entry SET quantity=2, meal_type='dinner' WHERE id=:id"),
            {"id": entry_id},
        )
        before_delete = connection.execute(
            text("SELECT nutrition_snapshot::text FROM diary_entry WHERE id=:id"),
            {"id": entry_id},
        ).scalar_one()
        connection.execute(text("DELETE FROM food WHERE id=:id"), {"id": food_id})
        preserved = connection.execute(
            text("SELECT food_id,nutrition_snapshot::text FROM diary_entry WHERE id=:id"),
            {"id": entry_id},
        ).one()
        assert preserved.food_id is None
        assert preserved.nutrition_snapshot == before_delete
    with engine.begin() as connection:
        with pytest.raises(DBAPIError, match="immutable"):
            connection.execute(
                text(
                    "UPDATE diary_entry SET nutrition_snapshot="
                    "CAST(:document AS jsonb) WHERE id=:id"
                ),
                {
                    "id": entry_id,
                    "document": json.dumps({"schema_version": 2, "changed": True}),
                },
            )
    downgrade = _run_alembic(url, "downgrade", "0010_target_plan_expand", check=False)
    assert downgrade.returncode != 0
    assert "Lossy Snapshot v2 downgrade prohibited" in downgrade.stderr
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
                  (id, created_by_principal_id, name, normalized_name, food_category_key,
                   nutrition_basis, default_unit_type,
                   unit_amount, unit_basis, calories, protein_g, carb_g, fat_g,
                   group_data_status, group_data_completeness, created_at, updated_at)
                VALUES
                  (:id, :principal, 'Concurrent contributions', 'concurrent contributions',
                   'other', 'per_100g',
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
                      (id, created_by_principal_id, food_id, group_key, amount_per_100_basis,
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


def _seed_plan009_food(url: str) -> tuple[UUID, UUID]:
    principal_id = uuid4()
    food_id = uuid4()
    engine = create_engine(url)
    with Session(engine) as session:
        session.add(Principal(id=principal_id))
        session.flush()
        session.add(
            Food(
                id=food_id,
                principal_id=principal_id,
                name="Plan 009 migration fixture",
                normalized_name="plan 009 migration fixture",
                food_category_key="other",
                nutrition_basis=NutritionBasis.per_100g,
                default_unit_type=DefaultUnitType.serving,
                unit_amount=100,
                unit_basis=UnitBasis.g,
                calories=100,
                protein_g=10,
                carb_g=20,
                fat_g=5,
            )
        )
        session.commit()
    engine.dispose()
    return principal_id, food_id


def _assert_plan009_special_value_failure(
    error: DBAPIError,
    special: str,
    constraint_names: str | frozenset[str],
) -> None:
    if special == "NaN":
        approved_names = (
            frozenset({constraint_names})
            if isinstance(constraint_names, str)
            else constraint_names
        )
        assert isinstance(error.orig, CheckViolation)
        assert error.orig.sqlstate == "23514"
        assert error.orig.diag.constraint_name in approved_names
        return
    assert isinstance(error.orig, NumericValueOutOfRange)
    assert error.orig.sqlstate == "22003"


@pytest.mark.migration
def test_plan009_existing_special_values_block_migration_with_field_counts() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0014_v2_food_taxonomy")
    _, food_id = _seed_plan009_food(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE food SET calories = CAST('NaN' AS numeric) WHERE id = :food"),
            {"food": food_id},
        )

    result = _run_alembic(url, "upgrade", "head", check=False)

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "Plan 009 cannot add finite Food constraints" in output
    assert "food.calories" in output
    assert "'1'" in output or ": 1" in output
    engine.dispose()


@pytest.mark.migration
def test_plan009_postgresql_constraints_reject_special_values_and_preserve_data() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, ("other",))
    _run_alembic(url, "upgrade", "head")
    principal_id = DEPLOYMENT_PRINCIPAL
    food_id = identifiers["other"]
    engine = create_engine(url)

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT constraint_record.conname,
                       constraint_record.convalidated,
                       constraint_record.conrelid::regclass::text AS table_name,
                       pg_get_constraintdef(constraint_record.oid) AS definition,
                       ARRAY(
                           SELECT attribute.attname
                           FROM pg_attribute AS attribute
                           WHERE attribute.attrelid = constraint_record.conrelid
                             AND attribute.attnum = ANY(constraint_record.conkey)
                           ORDER BY attribute.attname
                       ) AS column_names
                FROM pg_constraint AS constraint_record
                WHERE constraint_record.contype = 'c'
                  AND constraint_record.conname IN (
                      'ck_food_numeric_values_finite',
                      'ck_food_group_contribution_amount_finite'
                  )
                ORDER BY constraint_record.conname
                """
            )
        ).all()
    constraints = {row.conname: row for row in rows}
    assert set(constraints) == {
        "ck_food_numeric_values_finite",
        "ck_food_group_contribution_amount_finite",
    }
    expected_constraint_metadata = {
        "ck_food_numeric_values_finite": ("food", set(FOOD_NUMERIC_COLUMNS)),
        "ck_food_group_contribution_amount_finite": (
            "food_group_contribution",
            set(FOOD_GROUP_NUMERIC_COLUMNS),
        ),
    }
    for constraint_name, (table_name, expected_columns) in (
        expected_constraint_metadata.items()
    ):
        constraint = constraints[constraint_name]
        assert constraint.convalidated is True
        assert constraint.table_name == table_name
        assert set(constraint.column_names) == expected_columns
        for special in ("NaN", "Infinity", "-Infinity"):
            assert constraint.definition.count(f"'{special}'::numeric") == len(
                expected_columns
            )

    def insert_values(insert_id: UUID, name: str) -> dict[str, object]:
        return {
            "id": insert_id,
            "created_by_principal_id": principal_id,
            "updated_by_principal_id": principal_id,
            "name": name,
            "normalized_name": name.casefold(),
            "food_category_key": "other",
            "nutrition_basis": NutritionBasis.per_100g,
            "default_unit_type": DefaultUnitType.serving,
            "unit_amount": 100,
            "unit_basis": UnitBasis.g,
            "calories": 100,
            "protein_g": 10,
            "carb_g": 20,
            "fat_g": 5,
            "created_at": PLAN009_TIMESTAMP,
            "updated_at": PLAN009_TIMESTAMP,
        }

    for field in ("calories", "fiber_g"):
        for special in ("NaN", "Infinity", "-Infinity"):
            rejected_id = uuid4()
            values = insert_values(rejected_id, f"Rejected {field} {special}")
            values[field] = Decimal(special)
            with pytest.raises(DBAPIError) as rejected:
                with engine.begin() as connection:
                    connection.execute(Food.__table__.insert().values(**values))
            _assert_plan009_special_value_failure(
                rejected.value, special, "ck_food_numeric_values_finite"
            )
            with engine.connect() as connection:
                assert connection.execute(
                    text("SELECT count(*) FROM food WHERE id = :food"),
                    {"food": rejected_id},
                ).scalar_one() == 0

    for field in FOOD_NUMERIC_COLUMNS:
        with engine.connect() as connection:
            original = connection.execute(
                text(f"SELECT {field} FROM food WHERE id = :food"),
                {"food": food_id},
            ).one()[0]
        for special in ("NaN", "Infinity", "-Infinity"):
            with pytest.raises(DBAPIError) as rejected:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            f"UPDATE food SET {field} = CAST(:special AS numeric) "
                            "WHERE id = :food"
                        ),
                        {"special": special, "food": food_id},
                    )
            _assert_plan009_special_value_failure(
                rejected.value, special, "ck_food_numeric_values_finite"
            )
            with engine.connect() as connection:
                assert connection.execute(
                    text(f"SELECT {field} FROM food WHERE id = :food"),
                    {"food": food_id},
                ).one()[0] == original

    contribution_id = uuid4()
    with Session(engine) as session:
        session.add(
            FoodGroupContribution(
                id=contribution_id,
                principal_id=principal_id,
                food_id=food_id,
                group_key="fruits",
                amount_per_100_basis=100,
                data_status="known",
                food_group_rules_version="1.0.0",
            )
        )
        session.commit()
    for special in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(DBAPIError) as rejected:
            with engine.begin() as connection:
                connection.execute(
                    FoodGroupContribution.__table__.insert().values(
                        id=uuid4(),
                        created_by_principal_id=principal_id,
                        food_id=food_id,
                        group_key="vegetables",
                        amount_per_100_basis=Decimal(special),
                        data_status="known",
                        food_group_rules_version="1.0.0",
                        created_at=PLAN009_TIMESTAMP,
                        updated_at=PLAN009_TIMESTAMP,
                    )
                )
        _assert_plan009_special_value_failure(
            rejected.value, special, PLAN009_GROUP_NAN_CONSTRAINTS
        )
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT count(*) FROM food_group_contribution "
                    "WHERE food_id = :food AND group_key = 'vegetables'"
                ),
                {"food": food_id},
            ).scalar_one() == 0
    for special in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(DBAPIError) as rejected:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE food_group_contribution "
                        "SET amount_per_100_basis = CAST(:special AS numeric) WHERE id = :id"
                    ),
                    {"special": special, "id": contribution_id},
                )
        _assert_plan009_special_value_failure(
            rejected.value, special, PLAN009_GROUP_NAN_CONSTRAINTS
        )
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT amount_per_100_basis FROM food_group_contribution WHERE id = :id"
                ),
                {"id": contribution_id},
            ).scalar_one() == Decimal("100.000")

    maximum_food_id = food_id
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE food SET unit_amount=2000,calories=3000,protein_g=300,"
                "carb_g=500,fat_g=300,fiber_g=100,sodium_mg=50000,"
                "vitamin_d_mcg=250,sugar_g=0 WHERE id=:food"
            ),
            {"food": maximum_food_id},
        )
        before = connection.execute(
            text(
                "SELECT unit_amount, calories, protein_g, carb_g, fat_g, "
                "fiber_g, sodium_mg, vitamin_d_mcg, sugar_g "
                "FROM food WHERE id = :food"
            ),
            {"food": maximum_food_id},
        ).one()

    _run_alembic(url, "downgrade", "0014_v2_food_taxonomy")
    with engine.connect() as connection:
        during = connection.execute(
            text(
                "SELECT unit_amount, calories, protein_g, carb_g, fat_g, "
                "fiber_g, sodium_mg, vitamin_d_mcg, sugar_g "
                "FROM food WHERE id = :food"
            ),
            {"food": maximum_food_id},
        ).one()
    _run_alembic(url, "upgrade", "head")
    with engine.connect() as connection:
        after = connection.execute(
            text(
                "SELECT unit_amount, calories, protein_g, carb_g, fat_g, "
                "fiber_g, sodium_mg, vitamin_d_mcg, sugar_g "
                "FROM food WHERE id = :food"
            ),
            {"food": maximum_food_id},
        ).one()

    assert before == during == after
    assert tuple(before) == (
        Decimal("2000.00"),
        Decimal("3000.00"),
        Decimal("300.00"),
        Decimal("500.00"),
        Decimal("300.00"),
        Decimal("100.00"),
        Decimal("50000.00"),
        Decimal("250.00"),
        Decimal("0.00"),
    )
    engine.dispose()


def _prepare_plan012_0013_foods(
    url: str,
    legacy_primary_category_keys: tuple[str | None, ...],
) -> dict[str | None, UUID]:
    _reset_database(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,status,created_at,updated_at) "
                "VALUES (:id,'active',now(),now())"
            ),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
    engine.dispose()
    _run_alembic(url, "upgrade", "0013_v2_shared_food_catalog")

    identifiers: dict[str | None, UUID] = {}
    engine = create_engine(url)
    with engine.begin() as connection:
        for index, legacy_key in enumerate(legacy_primary_category_keys):
            food_id = uuid4()
            identifiers[legacy_key] = food_id
            connection.execute(
                text(
                    """
                    INSERT INTO food
                      (id,created_by_principal_id,name,normalized_name,category,
                       primary_category_key,nutrition_basis,default_unit_type,unit_amount,
                       unit_basis,calories,protein_g,carb_g,fat_g,created_at,updated_at)
                    VALUES
                      (:id,:principal,:name,:normalized_name,:category,:primary_category_key,
                       'per_100g','serving',100,'g',100,10,20,5,now(),now())
                    """
                ),
                {
                    "id": food_id,
                    "principal": DEPLOYMENT_PRINCIPAL,
                    "name": f"Plan 012 legacy fixture {index}",
                    "normalized_name": f"plan 012 legacy fixture {index}",
                    "category": f"Legacy category {index}",
                    "primary_category_key": legacy_key,
                },
            )
    engine.dispose()
    return identifiers


def _plan012_food_signature(url: str) -> tuple[tuple[object, ...], ...]:
    engine = create_engine(url)
    with engine.connect() as connection:
        signature = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT id,food_category_key,grain_type,baked_good_type,"
                    "grain_starch_type,taxonomy_review_required "
                    "FROM food ORDER BY id"
                )
            ).all()
        )
    engine.dispose()
    return signature


def _plan012_normalize_sql(value: object) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).split())


def _plan012_canonical_value(value: object) -> object:
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (
                    str(key),
                    _plan012_canonical_value(nested_value),
                )
                for key, nested_value in value.items()
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_plan012_canonical_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(
            sorted(
                (_plan012_canonical_value(item) for item in value),
                key=repr,
            )
        )
    return value


def _plan012_type_signature(sql_type: object) -> tuple[object, ...]:
    return (
        type(sql_type).__module__,
        type(sql_type).__qualname__,
        str(sql_type),
        getattr(sql_type, "length", None),
        getattr(sql_type, "precision", None),
        getattr(sql_type, "scale", None),
        getattr(sql_type, "timezone", None),
    )


def _plan012_canonical_table_signature(
    *,
    table_name: str,
    schema_name: str,
    columns: Sequence[Mapping[str, object]],
    primary_key: Mapping[str, object],
    foreign_keys: Sequence[Mapping[str, object]] = (),
    unique_constraints: Sequence[Mapping[str, object]] = (),
    check_constraints: Sequence[Mapping[str, object]] = (),
    indexes: Sequence[Mapping[str, object]] = (),
) -> tuple[object, ...]:
    column_names = [column.get("name") for column in columns]
    assert all(isinstance(name, str) and name for name in column_names)
    assert len(column_names) == len(set(column_names)), "Duplicate reflected column metadata"

    primary_key_columns = tuple(primary_key.get("constrained_columns") or ())
    canonical_columns = tuple(
        sorted(
            (
                (
                    column["name"],
                    _plan012_type_signature(column["type"]),
                    column.get("nullable"),
                    _plan012_normalize_sql(column.get("default")),
                    column["name"] in primary_key_columns,
                    _plan012_canonical_value(column.get("identity")),
                    _plan012_canonical_value(column.get("computed")),
                    column.get("autoincrement"),
                    column.get("comment"),
                )
                for column in columns
            ),
            key=lambda item: str(item[0]),
        )
    )
    canonical_primary_key = (
        primary_key.get("name"),
        primary_key_columns,
        _plan012_canonical_value(primary_key.get("dialect_options")),
    )
    canonical_foreign_keys = tuple(
        sorted(
            (
                (
                    foreign_key.get("name"),
                    tuple(foreign_key.get("constrained_columns") or ()),
                    foreign_key.get("referred_schema"),
                    foreign_key.get("referred_table"),
                    tuple(foreign_key.get("referred_columns") or ()),
                    _plan012_canonical_value(foreign_key.get("options")),
                    _plan012_canonical_value(foreign_key.get("dialect_options")),
                )
                for foreign_key in foreign_keys
            ),
            key=repr,
        )
    )
    canonical_unique_constraints = tuple(
        sorted(
            (
                (
                    constraint.get("name"),
                    tuple(constraint.get("column_names") or ()),
                    constraint.get("duplicates_index"),
                    _plan012_canonical_value(constraint.get("dialect_options")),
                )
                for constraint in unique_constraints
            ),
            key=repr,
        )
    )
    canonical_check_constraints = tuple(
        sorted(
            (
                (
                    constraint.get("name"),
                    _plan012_normalize_sql(constraint.get("sqltext")),
                    _plan012_canonical_value(constraint.get("dialect_options")),
                )
                for constraint in check_constraints
            ),
            key=repr,
        )
    )
    canonical_indexes = tuple(
        sorted(
            (
                (
                    index.get("name"),
                    index.get("unique"),
                    tuple(index.get("column_names") or ()),
                    tuple(index.get("expressions") or ()),
                    _plan012_canonical_value(index.get("column_sorting")),
                    index.get("duplicates_constraint"),
                    _plan012_canonical_value(index.get("dialect_options")),
                )
                for index in indexes
            ),
            key=repr,
        )
    )
    return (
        ("schema", schema_name),
        ("table", table_name),
        ("columns", canonical_columns),
        ("primary_key", canonical_primary_key),
        ("foreign_keys", canonical_foreign_keys),
        ("unique_constraints", canonical_unique_constraints),
        ("check_constraints", canonical_check_constraints),
        ("indexes", canonical_indexes),
    )


def _plan012_schema_signature(url: str) -> tuple[object, ...]:
    engine = create_engine(url)
    inspector = inspect(engine)
    table_name = "food"
    schema_name = inspector.default_schema_name
    signature = _plan012_canonical_table_signature(
        table_name=table_name,
        schema_name=schema_name,
        columns=inspector.get_columns(table_name, schema=schema_name),
        primary_key=inspector.get_pk_constraint(table_name, schema=schema_name),
        foreign_keys=inspector.get_foreign_keys(table_name, schema=schema_name),
        unique_constraints=inspector.get_unique_constraints(table_name, schema=schema_name),
        check_constraints=inspector.get_check_constraints(table_name, schema=schema_name),
        indexes=inspector.get_indexes(table_name, schema=schema_name),
    )
    engine.dispose()
    return signature


def test_plan012_schema_signature_normalizes_only_inspector_collection_order() -> None:
    id_column = {
        "name": "id",
        "type": String(36),
        "nullable": False,
        "default": None,
    }
    amount_column = {
        "name": "amount",
        "type": Numeric(8, 2),
        "nullable": False,
        "default": "0",
    }
    shared = {
        "table_name": "food",
        "schema_name": "public",
        "primary_key": {"name": "pk_food", "constrained_columns": ["id"]},
        "check_constraints": [
            {"name": "ck_food_amount", "sqltext": "amount >= 0"},
        ],
        "indexes": [
            {
                "name": "ix_food_amount_id",
                "unique": False,
                "column_names": ["amount", "id"],
            },
        ],
    }

    expected = _plan012_canonical_table_signature(
        columns=[id_column, amount_column],
        **shared,
    )
    reordered = _plan012_canonical_table_signature(
        columns=[amount_column, id_column],
        **shared,
    )
    changed_nullability = _plan012_canonical_table_signature(
        columns=[id_column, {**amount_column, "nullable": True}],
        **shared,
    )
    changed_index_order = _plan012_canonical_table_signature(
        columns=[id_column, amount_column],
        **{
            **shared,
            "indexes": [
                {
                    "name": "ix_food_amount_id",
                    "unique": False,
                    "column_names": ["id", "amount"],
                },
            ],
        },
    )

    assert reordered == expected
    assert changed_nullability != expected
    assert changed_index_order != expected


def _plan012_legacy_food_signature(url: str) -> tuple[tuple[object, ...], ...]:
    engine = create_engine(url)
    with engine.connect() as connection:
        signature = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT id,category,primary_category_key "
                    "FROM food ORDER BY id"
                )
            ).all()
        )
    engine.dispose()
    return signature


def _plan012_audit_signature(url: str) -> tuple[tuple[object, ...], ...]:
    engine = create_engine(url)
    with engine.connect() as connection:
        signature = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT food_id,legacy_category,legacy_primary_category_key "
                    "FROM food_taxonomy_v2_migration_audit ORDER BY food_id"
                )
            ).all()
        )
    engine.dispose()
    return signature


def _assert_plan012_guard_failure(
    url: str,
    before_food: tuple[tuple[object, ...], ...],
    before_schema: tuple[object, ...],
    expected_reason: str | None = None,
) -> None:
    result = _run_alembic(
        url, "downgrade", "0013_v2_shared_food_catalog", check=False
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "PLAN012_LOSSY_TAXONOMY_DOWNGRADE_BLOCKED" in output
    assert "plan012_lossy_taxonomy_downgrade_guard" in output
    if expected_reason is not None:
        assert expected_reason in output
    assert "NotNullViolation" not in output
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "5294eff9a956"
        )
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    engine.dispose()
    assert _plan012_food_signature(url) == before_food
    assert _plan012_schema_signature(url) == before_schema


@pytest.mark.migration
def test_plan012_exact_untouched_tuple_passes_guard_without_tracking_objects() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, ("whole_grains",))
    _run_alembic(url, "upgrade", "head")

    expected = _plan012_expected_tuple("whole_grains")
    assert _plan012_food_signature(url) == ((identifiers["whole_grains"], *expected),)
    _run_alembic(url, "downgrade", "df46234d2a7e")

    engine = create_engine(url)
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "df46234d2a7e"
        )
        plan012_triggers = connection.execute(
            text(
                "SELECT count(*) FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgname LIKE 'plan012%'"
            )
        ).scalar_one()
    assert plan012_triggers == 0
    assert not any(name.startswith("plan012") for name in inspector.get_table_names())
    engine.dispose()


@pytest.mark.migration
@pytest.mark.parametrize(
    ("scenario", "legacy_key"),
    (
        ("direct_update", "vegetables"),
        ("reviewed_resolution", "whole_grains"),
        ("new_food", "other"),
    ),
)
def test_plan012_direct_edits_reviewed_resolution_and_new_food_block_downgrade(
    scenario: str,
    legacy_key: str,
) -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, (legacy_key,))
    _run_alembic(url, "upgrade", "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        if scenario == "direct_update":
            connection.execute(
                text("UPDATE food SET food_category_key='fruits' WHERE id=:id"),
                {"id": identifiers[legacy_key]},
            )
        elif scenario == "reviewed_resolution":
            connection.execute(
                text(
                    "UPDATE food SET grain_starch_type='rice',"
                    "taxonomy_review_required=false WHERE id=:id"
                ),
                {"id": identifiers[legacy_key]},
            )
        else:
            connection.execute(
                text(
                    """
                    INSERT INTO food
                      (id,created_by_principal_id,name,normalized_name,food_category_key,
                       nutrition_basis,default_unit_type,unit_amount,unit_basis,
                       calories,protein_g,carb_g,fat_g,created_at,updated_at)
                    VALUES
                      (:id,:principal,'Plan 012 new Food','plan 012 new food','other',
                       'per_100g','serving',100,'g',100,10,20,5,now(),now())
                    """
                ),
                {"id": uuid4(), "principal": DEPLOYMENT_PRINCIPAL},
            )
    engine.dispose()

    _assert_plan012_guard_failure(
        url,
        before_food=_plan012_food_signature(url),
        before_schema=_plan012_schema_signature(url),
    )


@pytest.mark.migration
def test_plan012_untouched_upgrade_downgrade_reupgrade_preserves_exact_ledger() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, PLAN012_SAFE_LEGACY_CATEGORY_KEYS)
    legacy_before = _plan012_legacy_food_signature(url)
    legacy_schema_before = _plan012_schema_signature(url)

    _run_alembic(url, "upgrade", "head")
    v2_before = _plan012_food_signature(url)
    v2_schema_before = _plan012_schema_signature(url)
    audit_before = _plan012_audit_signature(url)
    actual_by_id = {row[0]: row[1:] for row in v2_before}
    assert actual_by_id == {
        food_id: _plan012_expected_tuple(legacy_key)
        for legacy_key, food_id in identifiers.items()
    }

    _run_alembic(url, "downgrade", "0013_v2_shared_food_catalog")
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0013_v2_shared_food_catalog"
        )
    engine.dispose()
    assert _plan012_legacy_food_signature(url) == legacy_before
    assert _plan012_schema_signature(url) == legacy_schema_before

    _run_alembic(url, "upgrade", "head")
    assert _plan012_food_signature(url) == v2_before
    assert _plan012_schema_signature(url) == v2_schema_before
    assert _plan012_audit_signature(url) == audit_before


@pytest.mark.migration
def test_plan012_legacy_null_origin_blocks_before_frozen_0014_downgrade() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, (None,))
    _run_alembic(url, "upgrade", "head")

    before_food = _plan012_food_signature(url)
    before_schema = _plan012_schema_signature(url)
    assert before_food == ((identifiers[None], *_plan012_expected_tuple(None)),)
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT count(*) FROM food_taxonomy_v2_migration_audit "
                "WHERE legacy_primary_category_key IS NULL"
            )
        ).scalar_one() == 1
    engine.dispose()

    _assert_plan012_guard_failure(
        url,
        before_food=before_food,
        before_schema=before_schema,
        expected_reason=(
            "legacy NULL-origin taxonomy cannot be restored safely through frozen revision 0014"
        ),
    )


@pytest.mark.migration
@pytest.mark.parametrize(
    ("field", "legacy_key", "update_sql"),
    (
        (
            "food_category_key",
            "vegetables",
            "UPDATE food SET food_category_key='fruits' WHERE id=:id",
        ),
        (
            "grain_type",
            "whole_grains",
            "UPDATE food SET grain_type='refined' WHERE id=:id",
        ),
        (
            "baked_good_type",
            "vegetables",
            "UPDATE food SET food_category_key='baked_goods',grain_type='unknown',"
            "baked_good_type='other' WHERE id=:id",
        ),
        (
            "grain_starch_type",
            "whole_grains",
            "UPDATE food SET grain_starch_type='rice' WHERE id=:id",
        ),
        (
            "taxonomy_review_required",
            "whole_grains",
            "UPDATE food SET taxonomy_review_required=false WHERE id=:id",
        ),
    ),
)
def test_plan012_each_v2_field_divergence_aborts_before_schema_or_data_loss(
    field: str,
    legacy_key: str,
    update_sql: str,
) -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, (legacy_key,))
    _run_alembic(url, "upgrade", "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text(update_sql), {"id": identifiers[legacy_key]})
    engine.dispose()

    before_food = _plan012_food_signature(url)
    assert dict(zip(PLAN012_V2_FIELDS, before_food[0][1:], strict=True))[field] is not None
    _assert_plan012_guard_failure(
        url,
        before_food=before_food,
        before_schema=_plan012_schema_signature(url),
    )


@pytest.mark.migration
def test_plan012_snapshot_v3_baseline_condition_blocks_at_current_head() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, ("other",))
    _run_alembic(url, "upgrade", "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO diary_entry
                  (id,principal_id,entry_date,food_id,quantity,meal_type,nutrition_snapshot,
                   target_plan_id,target_provenance,snapshot_schema_version,created_at)
                VALUES
                  (:id,:principal,'2026-07-29',:food,1,'breakfast',
                   CAST(:document AS jsonb),NULL,'legacy_unversioned',3,now())
                """
            ),
            {
                "id": uuid4(),
                "principal": DEPLOYMENT_PRINCIPAL,
                "food": identifiers["other"],
                "document": json.dumps({"schema_version": 3}),
            },
        )
    engine.dispose()

    _assert_plan012_guard_failure(
        url,
        before_food=_plan012_food_signature(url),
        before_schema=_plan012_schema_signature(url),
    )
