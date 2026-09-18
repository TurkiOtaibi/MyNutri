from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Barrier, Event
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from psycopg.errors import CheckViolation, NumericValueOutOfRange
from sqlalchemy import (
    CheckConstraint,
    Numeric,
    String,
    column,
    create_engine,
    inspect,
    table as sql_table,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import SQLModel, Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import current_diary_date
from app.models import (
    FOOD_NUMERIC_COLUMNS,
    DefaultUnitType,
    DiaryEntry,
    Food,
    NutritionBasis,
    NutritionDataSource,
    Principal,
    UnitBasis,
)
from app.schemas import (
    DiaryEntryCreate,
    DiaryEntryUpdate,
    FoodUpdate,
    ProfilePreview,
    TargetPlanWriteRequest,
)
from app.services.diary import (
    create_entry,
    create_entry_response,
    delete_entry,
    update_entry_response,
)
from app.services.food import delete_food, lock_food_namespace_for_logging, update_food_response
from app.services.profile import to_target_response
from app.services.target_plans import TargetPlanError, write_target_plan

BASELINE_HASHES = {
    "0001_initial.py": "8a4a122abcdc3da143a472c4317a5789aa8ba96828cc0ad168ea8b776ed138e4",
    "0002_foods_v1_per_basis.py": "8a148572e2ac061fc7815b8fe4c4a73eb61fbb4c3b648fec68b035b42c7cdb3a",
    "0003_diary_meal_type.py": "3df7b5160cc393a7df1a5ef3765b318a228df23fc26908ec8ed338ac57168929",
    "0004_principal_expand.py": "0a94bab7d92c73dc1a0bbf92c134aa1085be77cc857e0269b8b7deedeb2ba2b2",
    "0005_principal_backfill.py": "55e8f8d74d163ee407247d5921d1b9153d37a9df0460c966b1f1f4636cade560",
    "0006_principal_contract.py": "94b1bd94354ddbe295ce43611fac37da30d6e13400b3a545d4e828af8840dcd8",
    "0007_food_quality_expand.py": "4c3bdcec78e8eda39b1f0af68718e00a109e7324207c2703c9ecf8ef040ed088",
    "0008_food_groups_expand.py": "64e1a15017c45d3212eda268edf12cb962281e10f05f1a01a0509e8ad57cc8f5",
    "0009_legacy_target_transition_expand.py": "200d20c8325eb7763314edb8388afb33d6cd379a36733f21ce2871b4e28c47f9",
    "0010_target_plan_expand.py": "bdbf54f4b67cdeb0f58be6c24553c1dc1f0ca2f62d12751f0781f9d0eccd5a9a",
    "0011_diary_snapshot_v2_expand.py": "cd17529c25ec80c8daedbf566521a43e3398af5448888988b87e262ec5e916ea",
    "0012_v2_principal_auth_expand.py": "5892874ce4e5c80337cda4409c58a38c16f3748289e19996d3fd949852687f21",
    "0013_v2_shared_food_catalog.py": "d3ef7be045f1065cd29e67983611fba0aed58e4d5e098762636a9256b2bb7bf3",
    "0014_v2_food_taxonomy.py": "49fac55e9a500593a068a1835fc1d5882f8e9954fc1a128494e985e0f802aaec",
    "3f2e7b1c9a04_scope_target_plan_idempotency.py": "dae17300965446ba03b8e04398a0329e126bb5edcd640c836a5f5ab8e0a38052",
    "5294eff9a956_block_lossy_taxonomy_downgrade.py": "9b0705ec4521cfe6516413d7ddc4a040912c1ad8724b2b55225a5ba3bd4ecc3b",
    "7c4a9d2e1f06_enforce_positive_diary_quantity.py": "56466eef64421d14104ab174cf0745e3664c11df3c9d515c032dea20bfd9bb2e",
    "9f2a1b6c3d05_plan025_admin_diary_order_index.py": "727052a802eeee1d6e4f493fc7d21e963cf6f6de7a7b78b102bf42c3d7c2c152",
    "b7e31a4c9d20_add_diary_day_status.py": "cef968f1e3786213eef07a337e5a178501305dfb07a47a772a370a2f8c50d939",
    "c3a7e6d5f210_add_nutrition_pattern_analysis.py": "eb23950260d4e338c4a2db537a65eff594aad76d3caaee17aa4e3c32896f7617",
    "22733dbf5249_add_weekly_priorities_and_behavior_goals.py": "d340c5e285b45c461bf2a4820b346634611afce82f37de9f14e2802f668bb6e5",
    "df46234d2a7e_constrain_finite_food_nutrients.py": "70767434911230795129b4702f8d4bf2e9a4add9dcf1607c3fa648dfebdd0674",
    "8a91c4e7d2f6_nova_retirement_phase1.py": "ef99400d81aa6daa39f1551cf8c457e52744b5dc7f8b1d277d7b1fc4e001316e",
    "f47a2c9d6e13_retire_food_and_analysis_features.py": "0ced840bc07a4f1f46a3134ceb0ad40630a0e3ec1f19a48e65d9823ed087f104",
    "a6c81e4f2d90_retire_diary_day_status.py": "78666e664cd891a568645d204f8636a5f8b1bbf21b67a45807b3de9a2a91eefa",
    "b7d42e9a1c36_simplify_target_plans.py": "81f01a3291f9d846058636cfb597794e5dd6d51cdd0d8786b3317132df159894",
    "c8e53f0b2d47_retire_nutrition_versioning_and_legacy_targets.py": "60737aa5ddae07f966a5a43dcff8470be7272d35998d01728d60d21714b1870d",
    "d9f64a1c3e58_unify_food_catalog_and_cascade_diary_deletion.py": "140505cd27b921dbac6007630cb983e4512688e3e07f941efef6f7cbf5ef9888",
}
DEPLOYMENT_PRINCIPAL = UUID("00000000-0000-0000-0000-000000000001")
PLAN009_TIMESTAMP = datetime(2026, 7, 28, tzinfo=UTC)
TRANSITION_SNAPSHOT_REVISION = "0009_legacy_target_transition_expand"
SNAPSHOT_V2_REVISION = "0011_diary_snapshot_v2_expand"
PLAN009_FINITE_NUTRIENTS_REVISION = "df46234d2a7e"
PLAN012_GUARD_REVISION = "5294eff9a956"
PLAN012_DOWNGRADE_ERROR = "PLAN012_LOSSY_TAXONOMY_DOWNGRADE_BLOCKED"
PLAN012_DOWNGRADE_GUARD = "plan012_lossy_taxonomy_downgrade_guard"
PLAN021_REVISION = "3f2e7b1c9a04"
PLAN023_REVISION = "7c4a9d2e1f06"
PLAN025_REVISION = "9f2a1b6c3d05"
PLAN031_REVISION = "b7e31a4c9d20"
PLAN032_REVISION = "c3a7e6d5f210"
PLAN033_REVISION = "22733dbf5249"
NOVA_RETIREMENT_REVISION = "8a91c4e7d2f6"
NOVA_RETIREMENT_DOWNGRADE_ERROR = "NOVA_RETIREMENT_READER_FLOOR_REQUIRED"
FOOD_SIMPLIFICATION_REVISION = "f47a2c9d6e13"
DAY_STATUS_RETIREMENT_REVISION = "a6c81e4f2d90"
TARGET_PLAN_DATE_EFFECTIVE_REVISION = "b7d42e9a1c36"
TARGET_INTEGRITY_RETIREMENT_REVISION = "c8e53f0b2d47"
FOOD_CATALOG_UNIFICATION_REVISION = "d9f64a1c3e58"
PLAN023_CONSTRAINT = "ck_diary_entry_quantity_positive_finite"
PLAN023_PREFLIGHT_ERROR = "PLAN023_DIARY_QUANTITY_PREFLIGHT_BLOCKED"
PLAN023_PREFLIGHT_GUARD = "plan023_diary_quantity_positive_finite_preflight"
PLAN021_DOWNGRADE_ERROR = "PLAN021_TARGET_PLAN_IDEMPOTENCY_DOWNGRADE_BLOCKED"
PLAN021_DOWNGRADE_GUARD = "plan021_target_plan_idempotency_downgrade_guard"
HISTORICAL_FOOD_GROUP_NUMERIC_COLUMNS = ("amount_per_100_basis",)
HISTORICAL_FOOD_TABLE = sql_table(
    "food",
    *[
        column(name)
        for name in (
            "id",
            "created_by_principal_id",
            "updated_by_principal_id",
            "name",
            "normalized_name",
            "food_category_key",
            "nutrition_basis",
            "default_unit_type",
            "unit_amount",
            "unit_basis",
            "calories",
            "protein_g",
            "carb_g",
            "fat_g",
            "fiber_g",
            "created_at",
            "updated_at",
        )
    ],
)
HISTORICAL_FOOD_GROUP_TABLE = sql_table(
    "food_group_contribution",
    *[
        column(name)
        for name in (
            "id",
            "created_by_principal_id",
            "food_id",
            "group_key",
            "amount_per_100_basis",
            "data_status",
            "food_group_rules_version",
            "created_at",
            "updated_at",
        )
    ],
)
AUTHORITATIVE_HISTORICAL_CHECKS = {
    "profile": (
        "ck_profile_cut_intensity",
        "cut_intensity IN (0.150,0.200,0.250)",
    ),
}


POSTGRESQL_AUTHORITATIVE_CHECK_DEFINITIONS = {
    "ck_profile_cut_intensity": ("CHECK (cut_intensity = ANY (ARRAY[0.150, 0.200, 0.250]))"),
}
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
PLAN012_NON_NULL_LEGACY_CATEGORY_KEYS = tuple(
    key for key in PLAN012_LEGACY_CATEGORY_KEYS if key is not None
)
PLAN012_IRREVERSIBLE_REASON = (
    "Food Taxonomy V2 is intentionally irreversible because frozen revision 0014 "
    "cannot restore the exact prior category type and primary_category_key nullability"
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


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration rehearsals.")
    parsed = make_url(url)
    database = parsed.database or ""
    if (
        parsed.get_backend_name() != "postgresql"
        or parsed.host not in {"localhost", "127.0.0.1", "::1"}
        or not database.startswith("mynutri_test_")
    ):
        pytest.fail(
            "Migration tests require a literal-loopback PostgreSQL database with the "
            "mynutri_test_ prefix."
        )
    return url


def test_migration_database_url_requires_postgresql_loopback_test_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refused = (
        "sqlite:///mynutri_test_local",
        "postgresql+psycopg://postgres@db.internal:5432/mynutri_test_remote",
        "postgresql+psycopg://postgres@localhost.example.test:5432/mynutri_test_remote",
        "postgresql+psycopg://postgres@127.0.0.1:5432/not_a_test_database",
    )
    for url in refused:
        monkeypatch.setenv("TEST_DATABASE_URL", url)
        with pytest.raises(pytest.fail.Exception):
            _database_url()

    approved = "postgresql+psycopg://postgres@127.0.0.1:5432/mynutri_test_approved"
    monkeypatch.setenv("TEST_DATABASE_URL", approved)
    assert _database_url() == approved


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


def _normalized_check_expression(expression: str) -> str:
    normalized = "".join(expression.split())
    while normalized.startswith("(") and normalized.endswith(")"):
        depth = 0
        wraps_entire_expression = True
        for index, character in enumerate(normalized):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(normalized) - 1:
                    wraps_entire_expression = False
                    break
        if not wraps_entire_expression:
            break
        normalized = normalized[1:-1]
    return normalized


def _reset_database(url: str) -> None:
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS nova_retirement CASCADE"))
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


@pytest.fixture
def database_restored_to_current_head() -> Iterator[str]:
    url = _database_url()
    try:
        yield url
    finally:
        _reset_database(url)
        _run_alembic(url, "upgrade", "head")


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


def _normalized_revision_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _assert_immutable_revision_hashes(versions: Path) -> None:
    revision_files = {path.name for path in versions.glob("*.py")}
    assert revision_files == set(BASELINE_HASHES)
    actual = {name: _normalized_revision_hash(versions / name) for name in BASELINE_HASHES}
    assert actual == BASELINE_HASHES


@pytest.mark.migration
def test_immutable_baseline_revision_hashes() -> None:
    versions = Path(__file__).parents[1] / "alembic" / "versions"
    _assert_immutable_revision_hashes(versions)


@pytest.mark.migration
def test_authoritative_historical_checks_are_in_metadata_and_sqlite_safe() -> None:
    for table_name, (
        constraint_name,
        expected_expression,
    ) in AUTHORITATIVE_HISTORICAL_CHECKS.items():
        checks = [
            constraint
            for constraint in SQLModel.metadata.tables[table_name].constraints
            if isinstance(constraint, CheckConstraint)
        ]
        named = [constraint for constraint in checks if constraint.name == constraint_name]
        equivalent = [
            constraint
            for constraint in checks
            if _normalized_check_expression(str(constraint.sqltext))
            == _normalized_check_expression(expected_expression)
        ]

        assert len(named) == 1
        assert equivalent == named

    sqlite_engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(sqlite_engine)
    sqlite_inspector = inspect(sqlite_engine)
    sqlite_checks = {
        table_name: [
            constraint["name"] for constraint in sqlite_inspector.get_check_constraints(table_name)
        ]
        for table_name in AUTHORITATIVE_HISTORICAL_CHECKS
    }

    assert sqlite_checks["profile"].count("ck_profile_cut_intensity") == 1
    profile_insert = text(
        """
        INSERT INTO profile (
            id,
            principal_id,
            sex,
            birth_date,
            height_cm,
            weight_kg,
            activity_level,
            goal,
            protein_per_kg,
            fat_pct,
            cut_intensity,
            updated_at
        ) VALUES (
            :id,
            :principal_id,
            'male',
            '1990-01-01',
            175.00,
            75.00,
            'moderate',
            'cut',
            1.20,
            0.25,
            :cut_intensity,
            '2026-08-05 00:00:00'
        )
        """
    )
    with sqlite_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError, match="ck_profile_cut_intensity"):
            connection.execute(
                profile_insert,
                {
                    "id": str(uuid4()),
                    "principal_id": str(uuid4()),
                    "cut_intensity": 0.333,
                },
            )
        transaction.rollback()

        connection.execute(
            profile_insert,
            {
                "id": str(uuid4()),
                "principal_id": str(uuid4()),
                "cut_intensity": 0.200,
            },
        )
        connection.commit()

    sqlite_engine.dispose()


@pytest.mark.migration
def test_fresh_postgresql_upgrade_has_one_head_and_current_contract() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", TARGET_INTEGRITY_RETIREMENT_REVISION)

    engine = create_engine(url)
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            TARGET_INTEGRITY_RETIREMENT_REVISION
        )
        authoritative_checks = connection.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid, true) "
                "FROM pg_constraint "
                "WHERE conname IN "
                "('ck_profile_cut_intensity') "
                "ORDER BY conname"
            )
        ).all()
    assert len(authoritative_checks) == len(POSTGRESQL_AUTHORITATIVE_CHECK_DEFINITIONS)
    assert {
        name: _normalized_check_expression(definition) for name, definition in authoritative_checks
    } == {
        name: _normalized_check_expression(definition)
        for name, definition in POSTGRESQL_AUTHORITATIVE_CHECK_DEFINITIONS.items()
    }
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
    for retired_field in (
        "category",
        "food_category_key",
        "grain_type",
        "baked_good_type",
        "grain_starch_type",
        "taxonomy_review_required",
        "status",
        "food_kind",
        "group_data_status",
        "group_data_completeness",
        "nutrition_source_type",
        "nutrition_source_name",
        "nutrition_source_reference",
        "ingredients_text",
        "ingredients_source_type",
        "ingredients_source_name",
        "ingredients_source_reference",
        "nova_classification",
        "nova_review_status",
    ):
        assert retired_field not in food_columns
    assert food_columns["primary_category"]["nullable"] is False
    assert food_columns["subcategory"]["nullable"] is False
    assert food_columns["nutrition_data_source"]["nullable"] is False
    assert food_columns["ingredients"]["nullable"] is True
    for field in ("selenium_mcg", "iodine_mcg", "folate_dfe_mcg", "vitamin_a_rae_mcg"):
        assert food_columns[field]["nullable"] is True
        assert str(food_columns[field]["type"]) == "NUMERIC(10, 3)"
    retired_tables = {
        "food_group_contribution",
        "food_analytical_trait",
        "nutrition_analysis",
        "nutrition_analysis_revision",
        "nutrition_analysis_evidence_ref",
        "nutrition_analysis_revision_event",
        "nutrition_analysis_command_idempotency",
        "weekly_priority_recommendation",
        "weekly_priority_evaluation",
        "weekly_priority_evidence_ref",
        "behavior_goal",
        "behavior_goal_history",
        "behavior_goal_command_idempotency",
        "behavior_goal_reminder_delivery",
        "diary_day_status_history",
        "diary_day_status",
        "legacy_target_transition_snapshots",
    }
    assert retired_tables.isdisjoint(inspector.get_table_names())
    assert {"target_plan", "idempotency_record"}.issubset(inspector.get_table_names())
    target_plan_columns = {column["name"] for column in inspector.get_columns("target_plan")}
    assert target_plan_columns == {
        "id",
        "principal_id",
        "profile_id",
        "effective_from",
        "revision",
        "calculation_document",
        "created_at",
    }
    target_plan_uniques = {
        constraint["name"] for constraint in inspector.get_unique_constraints("target_plan")
    }
    assert {
        "uq_target_plan_id_principal",
        "uq_target_plan_principal_effective_revision",
    } <= target_plan_uniques
    target_plan_indexes = {index["name"] for index in inspector.get_indexes("target_plan")}
    assert "ix_target_plan_principal_effective_revision" in target_plan_indexes
    assert {
        "ix_target_plan_principal_effective",
        "uq_target_plan_one_active",
        "uq_target_plan_one_scheduled",
    }.isdisjoint(target_plan_indexes)
    with engine.connect() as connection:
        trigger_names = set(
            connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid='target_plan'::regclass AND NOT tgisinternal"
                )
            ).scalars()
        )
        assert trigger_names == {"target_plan_immutable_content_trigger"}
        assert (
            connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname='btree_gist'")
            ).scalar_one_or_none()
            is None
        )
    diary_columns = {column["name"]: column for column in inspector.get_columns("diary_entry")}
    assert diary_columns["target_plan_id"]["nullable"] is True
    assert "target_provenance" not in diary_columns
    assert diary_columns["food_id"]["nullable"] is False
    for field in ("recorded_unit_type", "recorded_unit_amount", "recorded_unit_basis"):
        assert diary_columns[field]["nullable"] is False
    assert diary_columns["recorded_unit_label"]["nullable"] is True
    assert "nutrition_snapshot" not in diary_columns
    assert "snapshot_schema_version" not in diary_columns
    diary_food_foreign_keys = [
        foreign_key
        for foreign_key in inspector.get_foreign_keys("diary_entry")
        if foreign_key["referred_table"] == "food"
    ]
    assert len(diary_food_foreign_keys) == 1
    assert diary_food_foreign_keys[0]["options"].get("ondelete") == "RESTRICT"
    engine.dispose()

@pytest.mark.migration
def test_food_catalog_unification_current_head_schema_and_security() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")

    engine = create_engine(url)
    inspector = inspect(engine)
    food_columns = {column["name"] for column in inspector.get_columns("food")}
    assert {"archived_at", "archived_by_principal_id"}.isdisjoint(food_columns)
    food_indexes = {index["name"] for index in inspector.get_indexes("food")}
    assert "ix_food_catalog_primary_category" in food_indexes
    assert "ix_food_catalog_primary_archived" not in food_indexes
    diary_food_fks = [
        foreign_key
        for foreign_key in inspector.get_foreign_keys("diary_entry")
        if foreign_key["referred_table"] == "food"
    ]
    assert len(diary_food_fks) == 1
    assert diary_food_fks[0]["options"].get("ondelete") == "CASCADE"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            FOOD_CATALOG_UNIFICATION_REVISION
        )
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            assert connection.execute(
                text("SELECT has_table_privilege(current_user, 'food', :privilege)"),
                {"privilege": privilege},
            ).scalar_one()
        assert connection.execute(
            text(
                "SELECT count(*) FROM information_schema.role_table_grants "
                "WHERE table_schema='public' AND table_name='food' AND grantee='PUBLIC' "
                "AND privilege_type IN ('INSERT','UPDATE','DELETE')"
            )
        ).scalar_one() == 0
    engine.dispose()

    check_result = _run_alembic(url, "check")
    check_output = check_result.stdout + check_result.stderr
    assert "alembic.autogenerate.checkconstraint_byname" in check_output
    assert "No new upgrade operations detected." in check_output


@pytest.mark.migration
def test_food_catalog_unification_revokes_data_api_food_mutation_and_preserves_backend() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", TARGET_INTEGRITY_RETIREMENT_REVISION)
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.begin() as connection:
        for role in ("anon", "authenticated", "service_role"):
            connection.execute(
                text(
                    f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') "
                    f"THEN CREATE ROLE {role}; END IF; END $$"
                )
            )
        connection.execute(text("GRANT ALL PRIVILEGES ON TABLE food TO PUBLIC"))
        connection.execute(text("GRANT ALL PRIVILEGES ON TABLE food TO anon, authenticated"))
        connection.execute(text("GRANT ALL PRIVILEGES ON TABLE food TO service_role"))
    engine.dispose()

    _run_alembic(url, "upgrade", "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        for role in ("anon", "authenticated"):
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                assert not connection.execute(
                    text("SELECT has_table_privilege(:role, 'food', :privilege)"),
                    {"role": role, "privilege": privilege},
                ).scalar_one()
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            assert connection.execute(
                text("SELECT has_table_privilege('service_role', 'food', :privilege)"),
                {"privilege": privilege},
            ).scalar_one()
            assert connection.execute(
                text("SELECT has_table_privilege(current_user, 'food', :privilege)"),
                {"privilege": privilege},
            ).scalar_one()
    engine.dispose()


@pytest.mark.migration
def test_food_catalog_unification_rejects_archived_data_atomically() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", TARGET_INTEGRITY_RETIREMENT_REVISION)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,role,status,created_at,updated_at) "
                "VALUES (:id,'admin','active',now(),now())"
            ),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
        connection.execute(
            text(
                "INSERT INTO food "
                "(id,created_by_principal_id,updated_by_principal_id,name,normalized_name,"
                "primary_category,subcategory,nutrition_basis,default_unit_type,unit_amount,"
                "unit_basis,calories,protein_g,carb_g,fat_g,nutrition_data_source,created_at,"
                "updated_at,archived_at,archived_by_principal_id) VALUES "
                "(:id,:principal,:principal,'Archived preflight','archived preflight','other',"
                "'other','per_100g','g',100,'g',100,1,2,3,'estimated',now(),now(),now(),:principal)"
            ),
            {"id": uuid4(), "principal": DEPLOYMENT_PRINCIPAL},
        )
    engine.dispose()

    result = _run_alembic(url, "upgrade", "head", check=False)
    assert result.returncode != 0
    assert "FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT: archived Food data exists" in (
        result.stdout + result.stderr
    )
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            TARGET_INTEGRITY_RETIREMENT_REVISION
        )
        assert connection.execute(text("SELECT count(*) FROM food")).scalar_one() == 1
        assert "archived_at" in {
            column["name"] for column in inspect(connection).get_columns("food")
        }
    engine.dispose()


@pytest.mark.migration
def test_food_catalog_unification_preserves_populated_rows_and_cascades_only_dependents(
    database_restored_to_current_head: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", TARGET_INTEGRITY_RETIREMENT_REVISION)
    principal_id = uuid4()
    profile_id = uuid4()
    plan_id = uuid4()
    deleted_food_id = uuid4()
    retained_food_id = uuid4()
    deleted_entry_id = uuid4()
    retained_entry_id = uuid4()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,role,status,created_at,updated_at) "
                "VALUES (:id,'user','active',now(),now())"
            ),
            {"id": principal_id},
        )
        connection.execute(
            text(
                "INSERT INTO profile "
                "(id,principal_id,sex,birth_date,height_cm,weight_kg,activity_level,goal,"
                "protein_per_kg,fat_pct,cut_intensity,updated_at) VALUES "
                "(:id,:principal,'male','1990-01-01',175,80,'moderate','maintain',"
                "1.2,0.25,0.2,now())"
            ),
            {"id": profile_id, "principal": principal_id},
        )
        connection.execute(
            text(
                "INSERT INTO target_plan "
                "(id,principal_id,profile_id,effective_from,revision,calculation_document,created_at) "
                "VALUES (:id,:principal,:profile,'2025-01-01',1,"
                "CAST(:document AS jsonb),now())"
            ),
            {
                "id": plan_id,
                "principal": principal_id,
                "profile": profile_id,
                "document": json.dumps({"target_result": {"calories": 2000}}),
            },
        )
        for food_id, name in (
            (deleted_food_id, "Cascade candidate"),
            (retained_food_id, "Retained catalog food"),
        ):
            connection.execute(
                text(
                    "INSERT INTO food "
                    "(id,created_by_principal_id,name,normalized_name,primary_category,"
                    "subcategory,nutrition_basis,default_unit_type,unit_amount,unit_basis,"
                    "calories,protein_g,carb_g,fat_g,nutrition_data_source,created_at,updated_at) "
                    "VALUES (:id,:principal,:name,:normalized,'other','other','per_100g',"
                    "'serving',100,'g',100,10,20,5,'estimated',now(),now())"
                ),
                {
                    "id": food_id,
                    "principal": principal_id,
                    "name": name,
                    "normalized": name.lower(),
                },
            )
        for entry_id, food_id in (
            (deleted_entry_id, deleted_food_id),
            (retained_entry_id, retained_food_id),
        ):
            connection.execute(
                text(
                    "INSERT INTO diary_entry "
                    "(id,principal_id,entry_date,food_id,target_plan_id,quantity,"
                    "recorded_unit_type,recorded_unit_amount,recorded_unit_basis,meal_type,created_at) "
                    "VALUES (:id,:principal,'2026-01-01',:food,:plan,1,'serving',100,'g',"
                    "'unspecified',now())"
                ),
                {
                    "id": entry_id,
                    "principal": principal_id,
                    "food": food_id,
                    "plan": plan_id,
                },
            )
    with engine.connect() as connection:
        before_foods = connection.execute(
            text(
                "SELECT id,name,archived_at,archived_by_principal_id FROM food "
                "ORDER BY id"
            )
        ).all()
        before_entries = connection.execute(
            text(
                "SELECT id,food_id,target_plan_id,quantity FROM diary_entry ORDER BY id"
            )
        ).all()
        before_plans = connection.execute(
            text(
                "SELECT id,principal_id,profile_id,effective_from,revision,calculation_document "
                "FROM target_plan ORDER BY id"
            )
        ).all()
    engine.dispose()

    _run_alembic(url, "upgrade", "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        after_foods = connection.execute(
            text("SELECT id,name,NULL,NULL FROM food ORDER BY id")
        ).all()
        after_entries = connection.execute(
            text(
                "SELECT id,food_id,target_plan_id,quantity FROM diary_entry ORDER BY id"
            )
        ).all()
        after_plans = connection.execute(
            text(
                "SELECT id,principal_id,profile_id,effective_from,revision,calculation_document "
                "FROM target_plan ORDER BY id"
            )
        ).all()
    assert after_foods == before_foods
    assert after_entries == before_entries
    assert after_plans == before_plans

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM food WHERE id=:id"), {"id": deleted_food_id})
    with engine.connect() as connection:
        assert connection.execute(text("SELECT id FROM food ORDER BY id")).scalars().all() == [
            retained_food_id
        ]
        assert connection.execute(
            text("SELECT id FROM diary_entry ORDER BY id")
        ).scalars().all() == [retained_entry_id]
        assert connection.execute(text("SELECT id FROM target_plan")).scalar_one() == plan_id
    engine.dispose()


@pytest.mark.migration
def test_food_catalog_unification_online_downgrade_refuses_without_mutation(
    database_restored_to_current_head: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")

    result = _run_alembic(
        url, "downgrade", TARGET_INTEGRITY_RETIREMENT_REVISION, check=False
    )

    assert result.returncode != 0
    assert "FOOD_CATALOG_SIMPLIFICATION_DOWNGRADE_BLOCKED" in result.stdout + result.stderr
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            FOOD_CATALOG_UNIFICATION_REVISION
        )
    engine.dispose()


def _seed_target_plan_revision_chain(url: str) -> tuple[UUID, UUID, UUID, UUID, UUID]:
    principal_id = uuid4()
    profile_id = uuid4()
    food_id = uuid4()
    revisions = (uuid4(), uuid4(), uuid4())
    legacy_record_id = uuid4()
    engine = create_engine(url)
    with engine.begin() as connection:
        today = connection.execute(
            text("SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date")
        ).scalar_one()
        effective_from = today - timedelta(days=5)
        connection.execute(
            text(
                "INSERT INTO principal (id,role,status,created_at,updated_at) "
                "VALUES (:id,'user','active',now(),now())"
            ),
            {"id": principal_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO profile
                  (id,principal_id,sex,birth_date,height_cm,weight_kg,activity_level,
                   goal,protein_per_kg,fat_pct,cut_intensity,updated_at)
                VALUES
                  (:id,:principal,'male','1990-01-01',175,80,'moderate','maintain',
                   1.2,0.25,0.2,now())
                """
            ),
            {"id": profile_id, "principal": principal_id},
        )
        document = json.dumps({"schema_version": 1, "target_result": {}})
        for index, plan_id in enumerate(revisions):
            final = index == len(revisions) - 1
            connection.execute(
                text(
                    """
                    INSERT INTO target_plan
                      (id,principal_id,profile_id,status,effective_from,effective_to,
                       calendar_timezone,predecessor_plan_id,superseded_by_plan_id,
                       activation_idempotency_key,calculation_document,
                       calculation_document_schema_version,calculation_engine_version,
                       nutrition_registry_version,created_at,activated_at,closed_at,
                       superseded_at)
                    VALUES
                      (:id,:principal,:profile,:status,:effective_from,NULL,'Asia/Riyadh',
                       :predecessor,:superseder,:key,CAST(:document AS jsonb),1,'2.0.0',
                       '4.0.0',now(),:activated_at,NULL,:superseded_at)
                    """
                ),
                {
                    "id": plan_id,
                    "principal": principal_id,
                    "profile": profile_id,
                    "status": "active" if final else "superseded_before_effective",
                    "effective_from": effective_from,
                    "predecessor": revisions[index - 1] if index else None,
                    "superseder": revisions[index + 1] if not final else None,
                    "key": f"migration-revision-{index + 1}",
                    "document": document,
                    "activated_at": datetime.now(UTC) if final else None,
                    "superseded_at": None if final else datetime.now(UTC),
                },
            )
        connection.execute(
            text(
                """
                INSERT INTO food
                  (id,created_by_principal_id,name,normalized_name,primary_category,
                   subcategory,nutrition_basis,default_unit_type,unit_amount,unit_basis,
                   calories,protein_g,carb_g,fat_g,nutrition_data_source,created_at,updated_at)
                VALUES
                  (:id,:principal,'Migration food','migration food','other','other',
                   'per_100g','serving',100,'g',100,10,20,5,'estimated',now(),now())
                """
            ),
            {"id": food_id, "principal": principal_id},
        )
        for entry_date in (today - timedelta(days=1), today):
            connection.execute(
                text(
                    """
                    INSERT INTO diary_entry
                      (id,principal_id,entry_date,food_id,quantity,meal_type,target_plan_id,
                       target_provenance,recorded_unit_type,recorded_unit_amount,
                       recorded_unit_basis,created_at)
                    VALUES
                      (:id,:principal,:entry_date,:food,1,'unspecified',:plan,
                       'versioned_plan','serving',100,'g',now())
                    """
                ),
                {
                    "id": uuid4(),
                    "principal": principal_id,
                    "entry_date": entry_date,
                    "food": food_id,
                    "plan": revisions[0],
                },
            )
        response = json.dumps(
            {
                "plan": {
                    "id": str(revisions[-1]),
                    "effective_from": effective_from.isoformat(),
                },
                "replaced_plan": None,
            }
        )
        connection.execute(
            text(
                """
                INSERT INTO idempotency_record
                  (id,principal_id,operation,idempotency_key,request_hash,state,
                   response_status,response_document,resource_type,resource_id,
                   created_at,completed_at,expires_at)
                VALUES
                  (:id,:principal,'target_plan.activate','legacy-replay',:request_hash,
                   'completed',201,CAST(:response AS jsonb),'target_plan',:resource,
                   now(),now(),now() + interval '1 day')
                """
            ),
            {
                "id": legacy_record_id,
                "principal": principal_id,
                "request_hash": "a" * 64,
                "response": response,
                "resource": revisions[-1],
            },
        )
    engine.dispose()
    return principal_id, food_id, revisions[0], revisions[-1], legacy_record_id


@pytest.mark.migration
def test_target_plan_and_integrity_cutovers_preserve_history_and_legacy_replay() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", DAY_STATUS_RETIREMENT_REVISION)
    principal_id, food_id, first_plan, final_plan, legacy_record = _seed_target_plan_revision_chain(
        url
    )

    _run_alembic(url, "upgrade", TARGET_PLAN_DATE_EFFECTIVE_REVISION)
    engine = create_engine(url)
    target_columns = {column["name"] for column in inspect(engine).get_columns("target_plan")}
    assert {
        "status",
        "effective_to",
        "calendar_timezone",
        "predecessor_plan_id",
        "superseded_by_plan_id",
        "activation_idempotency_key",
        "activated_at",
        "closed_at",
        "superseded_at",
    }.isdisjoint(target_columns)
    with engine.connect() as connection:
        today = connection.execute(
            text("SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date")
        ).scalar_one()
        revisions = (
            connection.execute(
                text(
                    "SELECT revision FROM target_plan WHERE principal_id=:principal "
                    "ORDER BY revision"
                ),
                {"principal": principal_id},
            )
            .scalars()
            .all()
        )
        assert revisions == [1, 2, 3]
        diary_bindings = connection.execute(
            text(
                "SELECT entry_date,target_plan_id FROM diary_entry "
                "WHERE principal_id=:principal ORDER BY entry_date"
            ),
            {"principal": principal_id},
        ).all()
        assert diary_bindings == [(today - timedelta(days=1), first_plan), (today, final_plan)]
        record = connection.execute(
            text(
                "SELECT operation,resource_id,response_document->'plan'->>'id' "
                "FROM idempotency_record WHERE id=:id"
            ),
            {"id": legacy_record},
        ).one()
        assert record == ("target_plan.activate", final_plan, str(final_plan))
        assert (
            connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname='btree_gist'")
            ).scalar_one_or_none()
            is None
        )

    with engine.connect() as connection:
        historical_document = connection.execute(
            text("SELECT calculation_document FROM target_plan WHERE id=:id"),
            {"id": final_plan},
        ).scalar_one()
    engine.dispose()

    _run_alembic(url, "upgrade", TARGET_INTEGRITY_RETIREMENT_REVISION)
    engine = create_engine(url)
    inspector = inspect(engine)
    assert {column["name"] for column in inspector.get_columns("target_plan")} == {
        "id",
        "principal_id",
        "profile_id",
        "effective_from",
        "revision",
        "calculation_document",
        "created_at",
    }
    assert "target_provenance" not in {
        column["name"] for column in inspector.get_columns("diary_entry")
    }
    assert not inspector.has_table("legacy_target_transition_snapshots")
    target_checks = {
        constraint["name"] for constraint in inspector.get_check_constraints("target_plan")
    }
    assert "ck_target_plan_calculation_document_shape" in target_checks
    assert "ck_target_plan_document_version" not in target_checks
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT calculation_document FROM target_plan WHERE id=:id"),
                {"id": final_plan},
            ).scalar_one()
            == historical_document
        )
        assert connection.execute(text("SELECT count(*) FROM target_plan")).scalar_one() == 3
        assert connection.execute(text("SELECT count(*) FROM diary_entry")).scalar_one() == 2
        record = connection.execute(
            text(
                "SELECT operation,resource_id,response_document->'plan'->>'id' "
                "FROM idempotency_record WHERE id=:id"
            ),
            {"id": legacy_record},
        ).one()
        assert record == ("target_plan.activate", final_plan, str(final_plan))

    for statement, parameters, message in (
        (
            "UPDATE target_plan SET calculation_document=calculation_document WHERE id=:id",
            {"id": final_plan},
            "Target Plan revisions are immutable",
        ),
        (
            "DELETE FROM target_plan WHERE id=:id",
            {"id": final_plan},
            "Target Plan revisions are immutable",
        ),
        (
            "UPDATE diary_entry SET target_plan_id=:final WHERE principal_id=:principal "
            "AND entry_date < (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date",
            {"final": final_plan, "principal": principal_id},
            "Historical Diary target binding is immutable",
        ),
        (
            "UPDATE diary_entry SET target_plan_id=:first WHERE principal_id=:principal "
            "AND entry_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date",
            {"first": first_plan, "principal": principal_id},
            "canonical Target Plan",
        ),
        (
            "INSERT INTO diary_entry "
            "(id,principal_id,entry_date,food_id,quantity,meal_type,target_plan_id,"
            "recorded_unit_type,recorded_unit_amount,"
            "recorded_unit_basis,created_at) VALUES "
            "(:entry,:principal,(CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date,"
            ":food,1,'unspecified',:first,'serving',100,'g',now())",
            {
                "entry": uuid4(),
                "principal": principal_id,
                "food": food_id,
                "first": first_plan,
            },
            "canonical Target Plan",
        ),
        (
            "INSERT INTO diary_entry "
            "(id,principal_id,entry_date,food_id,quantity,meal_type,target_plan_id,"
            "recorded_unit_type,recorded_unit_amount,"
            "recorded_unit_basis,created_at) VALUES "
            "(:entry,:principal,(CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Riyadh')::date,"
            ":food,1,'unspecified',NULL,'serving',100,'g',now())",
            {
                "entry": uuid4(),
                "principal": principal_id,
                "food": food_id,
            },
            "canonical Target Plan",
        ),
    ):
        with engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(DBAPIError, match=message):
                connection.execute(text(statement), parameters)
            transaction.rollback()
    engine.dispose()


def test_target_plan_date_model_downgrade_is_forward_only() -> None:
    result = _run_alembic(
        "postgresql+psycopg://offline:offline@127.0.0.1:5432/mynutri_test_offline",
        "downgrade",
        f"{TARGET_PLAN_DATE_EFFECTIVE_REVISION}:{DAY_STATUS_RETIREMENT_REVISION}",
        "--sql",
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "TARGET_PLAN_DATE_MODEL_DOWNGRADE_BLOCKED" in output
    assert "offline downgrade SQL is intentionally unavailable" in output
    assert "ADD COLUMN status" not in result.stdout

    retirement = _run_alembic(
        "postgresql+psycopg://offline:offline@127.0.0.1:5432/mynutri_test_offline",
        "downgrade",
        f"{TARGET_INTEGRITY_RETIREMENT_REVISION}:{TARGET_PLAN_DATE_EFFECTIVE_REVISION}",
        "--sql",
        check=False,
    )
    retirement_output = retirement.stdout + retirement.stderr
    assert retirement.returncode != 0
    assert "TARGET_INTEGRITY_RETIREMENT_DOWNGRADE_BLOCKED" in retirement_output
    assert "offline downgrade SQL is intentionally unavailable" in retirement_output
    assert "ADD COLUMN target_provenance" not in retirement.stdout


@pytest.mark.migration
def test_target_plan_date_model_preflight_rejects_invalid_legacy_replay_atomically() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", DAY_STATUS_RETIREMENT_REVISION)
    principal_id = uuid4()
    missing_plan_id = uuid4()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,role,status,created_at,updated_at) "
                "VALUES (:id,'user','active',now(),now())"
            ),
            {"id": principal_id},
        )
        connection.execute(
            text(
                "INSERT INTO idempotency_record "
                "(id,principal_id,operation,idempotency_key,request_hash,state,"
                "response_status,response_document,resource_type,resource_id,"
                "created_at,completed_at,expires_at) VALUES "
                "(:id,:principal,'target_plan.activate','invalid-legacy-replay',:hash,"
                "'completed',201,CAST(:response AS jsonb),'target_plan',:resource,"
                "now(),now(),now() + interval '1 day')"
            ),
            {
                "id": uuid4(),
                "principal": principal_id,
                "hash": "a" * 64,
                "response": json.dumps(
                    {
                        "plan": {
                            "id": str(missing_plan_id),
                            "effective_from": "2026-09-14",
                        },
                        "replaced_plan": None,
                    }
                ),
                "resource": missing_plan_id,
            },
        )
    engine.dispose()

    result = _run_alembic(url, "upgrade", TARGET_PLAN_DATE_EFFECTIVE_REVISION, check=False)

    assert result.returncode != 0
    assert "incompatible legacy idempotency record" in result.stderr
    engine = create_engine(url)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == DAY_STATUS_RETIREMENT_REVISION
        )
        assert "revision" not in {
            column["name"] for column in inspect(connection).get_columns("target_plan")
        }
        assert connection.execute(text("SELECT count(*) FROM idempotency_record")).scalar_one() == 1
    engine.dispose()


@pytest.mark.migration
def test_target_plan_date_model_preserves_btree_gist_when_an_application_dependency_exists() -> (
    None
):
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", DAY_STATUS_RETIREMENT_REVISION)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE btree_gist_dependency_probe ("
                "principal_id uuid NOT NULL, effective_period daterange NOT NULL, "
                "EXCLUDE USING gist (principal_id WITH =, effective_period WITH &&))"
            )
        )
    engine.dispose()

    result = _run_alembic(url, "upgrade", TARGET_PLAN_DATE_EFFECTIVE_REVISION, check=False)

    assert result.returncode != 0
    assert "btree_gist still has application dependencies" in result.stderr
    engine = create_engine(url)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == DAY_STATUS_RETIREMENT_REVISION
        )
        assert "revision" not in {
            column["name"] for column in inspect(connection).get_columns("target_plan")
        }
        assert (
            connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname='btree_gist'")
            ).scalar_one()
            == 1
        )
        assert inspect(connection).has_table("btree_gist_dependency_probe")
    engine.dispose()


@pytest.mark.migration
def test_day_status_retirement_is_selective_and_forward_only(
    database_restored_to_current_head: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", FOOD_SIMPLIFICATION_REVISION)
    principal_id = uuid4()
    status_id = uuid4()
    now = datetime.now(UTC)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,role,status,created_at,updated_at) "
                "VALUES (:id,'user','active',:now,:now)"
            ),
            {"id": principal_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO diary_day_status "
                "(id,principal_id,diary_date,status,version,entry_count,completed_at,"
                "created_at,updated_at) VALUES "
                "(:id,:principal_id,'2026-09-13','complete',4,0,:now,:now,:now)"
            ),
            {"id": status_id, "principal_id": principal_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO diary_day_status_history "
                "(id,day_status_id,principal_id,diary_date,from_status,to_status,event_type,"
                "day_version,actor_principal_id,occurred_at) VALUES "
                "(:id,:status_id,:principal_id,'2026-09-13','partial','complete','completed',"
                "4,:principal_id,:now)"
            ),
            {
                "id": uuid4(),
                "status_id": status_id,
                "principal_id": principal_id,
                "now": now,
            },
        )
        for operation, key, resource_type in (
            ("diary_day_complete", "complete", "diary_day_status"),
            ("diary_day_reopen", "reopen", "diary_day_status"),
            ("target_plan.activate", "target", "target_plan"),
            ("diary_day_complete", "other-resource", "target_plan"),
            ("unrelated_operation", "other-operation", "diary_day_status"),
        ):
            connection.execute(
                text(
                    "INSERT INTO idempotency_record "
                    "(id,principal_id,operation,idempotency_key,request_hash,state,"
                    "resource_type,created_at,expires_at) VALUES "
                    "(:id,:principal_id,:operation,:key,:request_hash,'in_progress',"
                    ":resource_type,:now,:expires_at)"
                ),
                {
                    "id": uuid4(),
                    "principal_id": principal_id,
                    "operation": operation,
                    "key": key,
                    "request_hash": key.ljust(64, "0"),
                    "resource_type": resource_type,
                    "now": now,
                    "expires_at": now + timedelta(days=7),
                },
            )
    engine.dispose()

    # Exercise the Day Logging Status cutover at its own historical boundary.
    # The next revision intentionally adds stricter Target Plan replay preflights.
    _run_alembic(url, "upgrade", DAY_STATUS_RETIREMENT_REVISION)
    engine = create_engine(url)
    inspector = inspect(engine)
    assert {"diary_day_status", "diary_day_status_history"}.isdisjoint(inspector.get_table_names())
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            DAY_STATUS_RETIREMENT_REVISION
        )
        remaining = connection.execute(
            text("SELECT operation,resource_type FROM idempotency_record ORDER BY idempotency_key")
        ).all()
    engine.dispose()
    assert set(remaining) == {
        ("target_plan.activate", "target_plan"),
        ("diary_day_complete", "target_plan"),
        ("unrelated_operation", "diary_day_status"),
    }

    blocked = _run_alembic(url, "downgrade", FOOD_SIMPLIFICATION_REVISION, check=False)
    assert blocked.returncode != 0
    assert "DIARY_DAY_STATUS_RETIREMENT_DOWNGRADE_BLOCKED" in (blocked.stdout + blocked.stderr)


@pytest.mark.migration
def test_plan033_tables_deny_supabase_data_api_roles_and_preserve_backend_owner() -> None:
    url = _database_url()
    _reset_database(url)
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        for role in ("anon", "authenticated"):
            exists = connection.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
            ).scalar_one_or_none()
            if exists is None:
                connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
    engine.dispose()
    _run_alembic(url, "upgrade", PLAN033_REVISION)
    tables = (
        "weekly_priority_recommendation",
        "weekly_priority_evaluation",
        "weekly_priority_evidence_ref",
        "behavior_goal",
        "behavior_goal_history",
        "behavior_goal_command_idempotency",
        "behavior_goal_reminder_delivery",
    )
    engine = create_engine(url)
    with engine.connect() as connection:
        goal_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='behavior_goal'"
                )
            )
        }
        assert {
            "last_progress_attempt_analysis_id",
            "last_progress_attempt_analysis_revision_id",
            "last_progress_attempt_analysis_revision",
            "last_progress_attempt_event_id",
            "last_progress_attempt_event_occurred_at",
        }.issubset(goal_columns)
        indexes = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE schemaname='public' AND tablename IN "
                    "('behavior_goal','behavior_goal_history',"
                    "'nutrition_analysis_revision_event')"
                )
            )
        }
        assert "ix_behavior_goal_finalized_unattempted" in indexes
        assert "ix_behavior_goal_finalized_attempt_revision" in indexes
        assert "ix_behavior_goal_finalized_attempt_event" in indexes
        for index_name in (
            "ix_behavior_goal_finalized_unattempted",
            "ix_behavior_goal_finalized_attempt_revision",
        ):
            assert "(state)::text = 'completed'::text" in indexes[index_name]
            assert "reviewed_at IS NOT NULL" in indexes[index_name]
        assert indexes["ix_behavior_goal_history_principal_occurred_id"].endswith(
            "(principal_id, occurred_at DESC, id DESC)"
        )
        assert indexes["ix_nutrition_analysis_event_owner_revision_time_id"].endswith(
            "(principal_id, revision_id, occurred_at, id)"
        )
        for table in tables:
            for role in ("anon", "authenticated"):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    assert (
                        connection.execute(
                            text("SELECT has_table_privilege(:role, :table, :privilege)"),
                            {"role": role, "table": f"public.{table}", "privilege": privilege},
                        ).scalar_one()
                        is False
                    )
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                assert (
                    connection.execute(
                        text("SELECT has_table_privilege(current_user, :table, :privilege)"),
                        {"table": f"public.{table}", "privilege": privilege},
                    ).scalar_one()
                    is True
                )
    for role in ("anon", "authenticated"):
        for table in tables:
            for statement in (
                f"SELECT * FROM public.{table} LIMIT 1",
                f"INSERT INTO public.{table} DEFAULT VALUES",
            ):
                with engine.connect() as connection:
                    transaction = connection.begin()
                    connection.execute(text(f"SET LOCAL ROLE {role}"))
                    with pytest.raises(DBAPIError, match="permission denied"):
                        connection.execute(text(statement))
                    transaction.rollback()
    engine.dispose()


def _seed_plan021_profile(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,status,created_at,updated_at) "
                "VALUES (:id,'active',now(),now())"
            ),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
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
            {"id": uuid4(), "principal": DEPLOYMENT_PRINCIPAL},
        )
    engine.dispose()


def _add_current_food(engine, name: str) -> UUID:
    food_id = uuid4()
    with Session(engine) as session:
        session.add(
            Food(
                id=food_id,
                principal_id=DEPLOYMENT_PRINCIPAL,
                name=name,
                normalized_name=name.casefold(),
                primary_category="other",
                subcategory="other",
                nutrition_basis=NutritionBasis.per_100g,
                default_unit_type=DefaultUnitType.g,
                unit_amount=1,
                unit_basis=UnitBasis.g,
                calories=100,
                protein_g=1,
                carb_g=2,
                fat_g=3,
                nutrition_data_source=NutritionDataSource.estimated,
            )
        )
        session.commit()
    return food_id


def _plan021_draft(weight: float) -> ProfilePreview:
    return ProfilePreview(
        sex="male",
        birth_date=date(1990, 1, 1),
        height_cm=175,
        weight_kg=weight,
        activity_level="moderate",
        goal="maintain",
        protein_per_kg=1.2,
        fat_pct=0.25,
        selected_cut_intensity=0.2,
    )


def _current_target_write_request(
    weight: float, effective_from: date | None = None
) -> TargetPlanWriteRequest:
    draft = _plan021_draft(weight)
    requested_date = effective_from or current_diary_date()
    preview = to_target_response(draft, requested_date)
    return TargetPlanWriteRequest(
        **draft.model_dump(),
        effective_from=requested_date,
        confirmed=True,
        expected_preview_hash=preview.preview_hash,
    )


def _write_current_target(
    engine,
    request: TargetPlanWriteRequest,
    key: str,
) -> tuple[str, bool]:
    with Session(engine) as session:
        response, replayed = write_target_plan(
            session,
            PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
            request,
            key,
        )
        return str(response.plan.id), replayed


def _seed_plan021_operation(engine, key: str, operation: str) -> str:
    """Populate the frozen lifecycle schema without coupling it to current services."""
    plan_id = uuid4()
    with engine.begin() as connection:
        profile_id = connection.execute(
            text("SELECT id FROM profile WHERE principal_id=:principal"),
            {"principal": DEPLOYMENT_PRINCIPAL},
        ).scalar_one()
        prior = connection.execute(
            text(
                "SELECT id FROM target_plan WHERE principal_id=:principal "
                "AND status='scheduled' ORDER BY created_at DESC LIMIT 1"
            ),
            {"principal": DEPLOYMENT_PRINCIPAL},
        ).scalar_one_or_none()
        if prior is not None:
            connection.execute(
                text(
                    "UPDATE target_plan SET status='superseded_before_effective', "
                    "superseded_by_plan_id=:new_id, superseded_at=now() WHERE id=:prior"
                ),
                {"new_id": plan_id, "prior": prior},
            )
        document = json.dumps(
            {"schema_version": 1, "target_result": {"fixture": "historical-plan021"}}
        )
        connection.execute(
            text(
                """
                INSERT INTO target_plan
                  (id,principal_id,profile_id,status,effective_from,effective_to,
                   calendar_timezone,predecessor_plan_id,superseded_by_plan_id,
                   activation_idempotency_key,calculation_document,
                   calculation_document_schema_version,calculation_engine_version,
                   nutrition_registry_version,created_at,activated_at,closed_at,superseded_at)
                VALUES
                  (:id,:principal,:profile,'scheduled',CURRENT_DATE + 1,NULL,
                   'Asia/Riyadh',:prior,NULL,:key,CAST(:document AS jsonb),1,
                   'historical-fixture','historical-fixture',now(),NULL,NULL,NULL)
                """
            ),
            {
                "id": plan_id,
                "principal": DEPLOYMENT_PRINCIPAL,
                "profile": profile_id,
                "prior": prior,
                "key": key,
                "document": document,
            },
        )
        response = json.dumps({"plan": {"id": str(plan_id)}, "replaced_plan": None})
        connection.execute(
            text(
                """
                INSERT INTO idempotency_record
                  (id,principal_id,operation,idempotency_key,request_hash,state,
                   response_status,response_document,resource_type,resource_id,
                   created_at,completed_at,expires_at)
                VALUES
                  (:id,:principal,:operation,:key,:request_hash,'completed',201,
                   CAST(:response AS jsonb),'target_plan',:plan_id,now(),now(),now() + interval '1 day')
                """
            ),
            {
                "id": uuid4(),
                "principal": DEPLOYMENT_PRINCIPAL,
                "operation": operation,
                "key": key,
                "request_hash": hashlib.sha256(f"{operation}:{key}".encode()).hexdigest(),
                "response": response,
                "plan_id": plan_id,
            },
        )
    return str(plan_id)


def _plan021_schema_signature(url: str) -> tuple[frozenset[str], ...]:
    engine = create_engine(url)
    inspector = inspect(engine)
    target_uniques = frozenset(
        constraint["name"] for constraint in inspector.get_unique_constraints("target_plan")
    )
    ledger_uniques = frozenset(
        constraint["name"] for constraint in inspector.get_unique_constraints("idempotency_record")
    )
    target_indexes = frozenset(index["name"] for index in inspector.get_indexes("target_plan"))
    target_foreign_keys = frozenset(
        constraint["name"]
        for constraint in inspector.get_foreign_keys("target_plan")
        if constraint["name"] is not None
    )
    with engine.connect() as connection:
        target_triggers = frozenset(
            connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid='target_plan'::regclass AND NOT tgisinternal"
                )
            ).scalars()
        )
    engine.dispose()
    return (
        target_uniques,
        ledger_uniques,
        target_indexes,
        target_foreign_keys,
        target_triggers,
    )


def _plan021_data_signature(url: str) -> tuple[tuple[tuple[object, ...], ...], ...]:
    engine = create_engine(url)
    with engine.connect() as connection:
        plans = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT id::text,principal_id::text,status,activation_idempotency_key,"
                    "predecessor_plan_id::text,superseded_by_plan_id::text "
                    "FROM target_plan ORDER BY id"
                )
            ).all()
        )
        records = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT operation,idempotency_key,state,response_status,resource_id::text "
                    "FROM idempotency_record ORDER BY operation,idempotency_key"
                )
            ).all()
        )
        profiles = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT principal_id::text,weight_kg::text,updated_at::text "
                    "FROM profile ORDER BY principal_id"
                )
            ).all()
        )
    engine.dispose()
    return plans, records, profiles


def _assert_plan021_operation_scoped_schema(url: str) -> None:
    (
        target_uniques,
        ledger_uniques,
        target_indexes,
        target_foreign_keys,
        target_triggers,
    ) = _plan021_schema_signature(url)
    assert "uq_target_plan_principal_key" not in target_uniques
    assert "uq_target_plan_id_principal" in target_uniques
    assert "uq_idempotency_scope" in ledger_uniques
    assert {"uq_target_plan_one_active", "uq_target_plan_one_scheduled"}.issubset(target_indexes)
    assert {
        "fk_target_plan_profile_owner",
        "fk_target_plan_predecessor_owner",
        "fk_target_plan_superseding_owner",
    }.issubset(target_foreign_keys)
    assert "target_plan_immutable_content_trigger" in target_triggers


@pytest.mark.migration
def test_plan021_fresh_upgrade_keeps_ledger_as_replay_authority() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", PLAN021_REVISION)

    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN021_REVISION
        )
    engine.dispose()
    _assert_plan021_operation_scoped_schema(url)


@pytest.mark.migration
def test_plan021_populated_upgrade_preserves_plan_and_ledger_rows() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "5294eff9a956")
    _seed_plan021_profile(url)
    engine = create_engine(url)
    plan_id = _seed_plan021_operation(engine, "plan021-populated-upgrade", "target_plan.activate")
    engine.dispose()
    before = _plan021_data_signature(url)
    assert before[0][0][0] == plan_id
    assert before[1] == (
        ("target_plan.activate", "plan021-populated-upgrade", "completed", 201, plan_id),
    )

    _run_alembic(url, "upgrade", PLAN021_REVISION)

    assert _plan021_data_signature(url) == before
    _assert_plan021_operation_scoped_schema(url)


def test_plan021_offline_downgrade_fails_before_constraint_sql() -> None:
    result = _run_alembic(
        "postgresql+psycopg://offline:offline@127.0.0.1:5432/mynutri_test_offline",
        "downgrade",
        f"{PLAN021_REVISION}:5294eff9a956",
        "--sql",
        check=False,
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert PLAN021_DOWNGRADE_ERROR in output
    assert PLAN021_DOWNGRADE_GUARD in output
    assert PLAN012_DOWNGRADE_ERROR not in output
    assert PLAN012_DOWNGRADE_GUARD not in output
    assert "offline downgrade SQL is intentionally unavailable" in output
    assert "ADD CONSTRAINT uq_target_plan_principal_key" not in result.stdout
    assert "ALTER TABLE" not in result.stdout
    assert "UPDATE " not in result.stdout
    assert "DELETE " not in result.stdout


@pytest.mark.migration
def test_plan021_downgrade_restores_constraint_before_cross_operation_reuse() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", PLAN021_REVISION)
    _seed_plan021_profile(url)
    engine = create_engine(url)
    _seed_plan021_operation(engine, "plan021-single-operation", "target_plan.activate")
    engine.dispose()
    before = _plan021_data_signature(url)

    _run_alembic(url, "downgrade", "5294eff9a956")

    engine = create_engine(url)
    inspector = inspect(engine)
    target_uniques = {
        constraint["name"] for constraint in inspector.get_unique_constraints("target_plan")
    }
    ledger_uniques = {
        constraint["name"] for constraint in inspector.get_unique_constraints("idempotency_record")
    }
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "5294eff9a956"
        )
    engine.dispose()
    assert "uq_target_plan_principal_key" in target_uniques
    assert "uq_idempotency_scope" in ledger_uniques
    assert _plan021_data_signature(url) == before

    _run_alembic(url, "upgrade", PLAN021_REVISION)
    assert _plan021_data_signature(url) == before
    _assert_plan021_operation_scoped_schema(url)


@pytest.mark.migration
def test_plan021_downgrade_blocks_duplicate_visible_keys_atomically() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", PLAN021_REVISION)
    _seed_plan021_profile(url)
    engine = create_engine(url)
    shared_key = "plan021-legitimate-cross-operation"
    activation_id = _seed_plan021_operation(engine, shared_key, "target_plan.activate")
    replacement_id = _seed_plan021_operation(engine, shared_key, "target_plan.replace")
    engine.dispose()
    assert activation_id != replacement_id
    before_data = _plan021_data_signature(url)
    before_schema = _plan021_schema_signature(url)
    assert len(before_data[0]) == 2
    assert {(record[0], record[1], record[4]) for record in before_data[1]} == {
        ("target_plan.activate", shared_key, activation_id),
        ("target_plan.replace", shared_key, replacement_id),
    }
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN021_REVISION
        )
    engine.dispose()

    result = _run_alembic(url, "downgrade", "5294eff9a956", check=False)
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert PLAN021_DOWNGRADE_ERROR in output
    assert PLAN021_DOWNGRADE_GUARD in output
    assert PLAN012_DOWNGRADE_ERROR not in output
    assert PLAN012_DOWNGRADE_GUARD not in output
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN021_REVISION
        )
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    engine.dispose()
    assert _plan021_data_signature(url) == before_data
    assert _plan021_schema_signature(url) == before_schema
    _assert_plan021_operation_scoped_schema(url)


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
    # Exercise the transition-snapshot guard at its historical boundary, below Plan 012.
    _run_alembic(url, "upgrade", TRANSITION_SNAPSHOT_REVISION)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO profile
                  (id,principal_id,sex,birth_date,height_cm,weight_kg,activity_level,goal,
                   protein_per_kg,fat_pct,updated_at)
                VALUES
                  (:id,:principal,'male','1990-01-01',175,80,'moderate','maintain',
                   1.2,0.25,now())
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
                text(
                    "UPDATE legacy_target_transition_snapshots SET transition_date='2026-07-17' WHERE id=:id"
                ),
                {"id": snapshot_id},
            )
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT transition_date FROM legacy_target_transition_snapshots WHERE id=:id"),
            {"id": snapshot_id},
        ).scalar_one() == date(2026, 7, 16)
    downgrade = _run_alembic(url, "downgrade", "0008_food_groups_expand", check=False)
    assert downgrade.returncode != 0
    assert "Lossy downgrade of transition snapshots is prohibited." in downgrade.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            TRANSITION_SNAPSHOT_REVISION
        )
        assert connection.execute(
            text("SELECT transition_date FROM legacy_target_transition_snapshots WHERE id=:id"),
            {"id": snapshot_id},
        ).scalar_one() == date(2026, 7, 16)
        assert connection.execute(text("SELECT 1")).scalar_one() == 1

    retirement = _run_alembic(url, "upgrade", TARGET_INTEGRITY_RETIREMENT_REVISION, check=False)
    assert retirement.returncode != 0
    assert "legacy transition data exists" in retirement.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            TRANSITION_SNAPSHOT_REVISION
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM legacy_target_transition_snapshots")
            ).scalar_one()
            == 1
        )
    engine.dispose()


@pytest.mark.migration
def test_populated_backfill_fails_closed_then_reconciles_without_history_change() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0003_diary_meal_type")
    identifiers = _seed_0003(url)
    engine = create_engine(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")

    absent = _run_alembic(url, "upgrade", TARGET_PLAN_DATE_EFFECTIVE_REVISION, check=False)
    assert absent.returncode != 0
    assert "exactly one explicitly provisioned active Principal" in absent.stderr

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id, status, created_at, updated_at) VALUES (:id, 'active', now(), now())"
            ),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
    _run_alembic(url, "upgrade", TARGET_PLAN_DATE_EFFECTIVE_REVISION)

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
        migrated_diary = connection.execute(
            text(
                "SELECT target_plan_id, target_provenance, food_id, recorded_unit_type, "
                "recorded_unit_amount, recorded_unit_basis, recorded_unit_label "
                "FROM diary_entry WHERE id = :id"
            ),
            {"id": identifiers["diary"]},
        ).one()
        assert tuple(migrated_diary) == (
            None,
            "legacy_unversioned",
            identifiers["food"],
            "serving",
            Decimal("100.0000"),
            "g",
            None,
        )
        migrated_food = connection.execute(
            text(
                """
                SELECT primary_category, subcategory, nutrition_data_source, ingredients,
                       selenium_mcg, iodine_mcg, folate_dfe_mcg, vitamin_a_rae_mcg
                  FROM food WHERE id = :id
                """
            ),
            {"id": identifiers["food"]},
        ).one()
        assert tuple(migrated_food) == (
            "other",
            "other",
            "estimated",
            None,
            None,
            None,
            None,
            None,
        )
        current_tables = set(inspect(connection).get_table_names())
        assert "food_group_contribution" not in current_tables
        assert "food_analytical_trait" not in current_tables
        current_diary_columns = {
            column["name"] for column in inspect(connection).get_columns("diary_entry")
        }
        assert "nutrition_snapshot" not in current_diary_columns
        assert "snapshot_schema_version" not in current_diary_columns

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

    retirement = _run_alembic(url, "upgrade", TARGET_INTEGRITY_RETIREMENT_REVISION, check=False)
    assert retirement.returncode != 0
    assert "Diary provenance cannot be represented by target_plan_id alone" in retirement.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            TARGET_PLAN_DATE_EFFECTIVE_REVISION
        )
        assert "target_provenance" in {
            column["name"] for column in inspect(connection).get_columns("diary_entry")
        }
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
    # Exercise the Snapshot v2 guard at its historical boundary, below Plan 012.
    _run_alembic(url, "upgrade", SNAPSHOT_V2_REVISION)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO food
                  (id,principal_id,name,
                   nutrition_basis,default_unit_type,unit_amount,unit_basis,
                   calories,protein_g,carb_g,fat_g,created_at,updated_at)
                VALUES
                  (:id,:principal,'Snapshot source','per_100g','serving',100,'g',
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
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            SNAPSHOT_V2_REVISION
        )
        assert (
            connection.execute(
                text("SELECT nutrition_snapshot::text FROM diary_entry WHERE id=:id"),
                {"id": entry_id},
            ).scalar_one()
            == before_delete
        )
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
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
    _run_alembic(url, "upgrade", TARGET_PLAN_DATE_EFFECTIVE_REVISION)


@pytest.mark.migration
def test_concurrent_first_future_writes_create_two_revisions_without_snapshot() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "0004_principal_expand")
    engine = create_engine(url)
    profile_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,status,created_at,updated_at) VALUES (:id,'active',now(),now())"
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
    effective_from = current_diary_date() + timedelta(days=1)
    barrier = Barrier(2)

    def write(weight_and_key: tuple[float, str]) -> tuple[str, int]:
        weight, key = weight_and_key
        with Session(engine) as session:
            barrier.wait(timeout=10)
            response, replayed = write_target_plan(
                session,
                PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                _current_target_write_request(weight, effective_from),
                key,
            )
            assert replayed is False
            return str(response.plan.id), response.plan.revision

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(write, ((82, "race-a"), (84, "race-b"))))
    assert len({plan_id for plan_id, _ in results}) == 2
    assert {revision for _, revision in results} == {1, 2}
    with engine.connect() as connection:
        assert not inspect(connection).has_table("legacy_target_transition_snapshots")
        assert connection.execute(text("SELECT count(*) FROM target_plan")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM idempotency_record")).scalar_one() == 2
    engine.dispose()


@pytest.mark.migration
def test_concurrent_plan_and_future_diary_creation_finish_with_canonical_binding() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(
        url,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"},
    )
    food_id = uuid4()
    with Session(engine) as session:
        session.add(
            Food(
                id=food_id,
                principal_id=DEPLOYMENT_PRINCIPAL,
                name="Concurrent binding food",
                normalized_name="concurrent binding food",
                primary_category="other",
                subcategory="other",
                nutrition_basis=NutritionBasis.per_100g,
                default_unit_type=DefaultUnitType.g,
                unit_amount=1,
                unit_basis=UnitBasis.g,
                calories=100,
                protein_g=1,
                carb_g=2,
                fat_g=3,
                nutrition_data_source=NutritionDataSource.estimated,
            )
        )
        session.commit()

    _write_current_target(engine, _current_target_write_request(80), "current-plan")
    effective_from = current_diary_date() + timedelta(days=1)
    future_request = _current_target_write_request(84, effective_from)
    barrier = Barrier(2)

    def write_future_plan() -> str:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            response, _ = write_target_plan(
                session,
                PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                future_request,
                "future-plan",
            )
            return str(response.plan.id)

    def write_future_diary() -> str:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            entry = create_entry(
                session,
                PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                DiaryEntryCreate(
                    entry_date=effective_from,
                    food_id=food_id,
                    quantity=1,
                ),
            )
            return str(entry.id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        plan_future = executor.submit(write_future_plan)
        diary_future = executor.submit(write_future_diary)
        plan_id = plan_future.result(timeout=30)
        diary_id = diary_future.result(timeout=30)

    with engine.connect() as connection:
        binding = connection.execute(
            text("SELECT target_plan_id::text FROM diary_entry WHERE id=:entry"),
            {"entry": diary_id},
        ).scalar_one()
        assert binding == plan_id
    engine.dispose()


@pytest.mark.migration
@pytest.mark.parametrize("mutation", ("create", "update", "delete"))
def test_food_delete_serializes_with_diary_mutations_and_keeps_responses_atomic(
    mutation: str,
) -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(
        url,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"},
    )
    food_id = _add_current_food(engine, f"Diary race {mutation}")
    principal = PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL)
    entry_id: UUID | None = None
    if mutation != "create":
        with Session(engine) as session:
            entry_id = create_entry(
                session,
                principal,
                DiaryEntryCreate(
                    entry_date=current_diary_date(),
                    food_id=food_id,
                    quantity=1,
                ),
            ).id

    delete_started = Event()

    def concurrent_delete() -> int:
        delete_started.set()
        with Session(engine) as session:
            delete_food(session, principal, food_id)
        return 204

    with Session(engine) as mutation_session:
        mutation_session.exec(
            select(Principal)
            .where(Principal.id == DEPLOYMENT_PRINCIPAL)
            .with_for_update()
        ).one()
        lock_food_namespace_for_logging(mutation_session)
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending_delete = executor.submit(concurrent_delete)
            assert delete_started.wait(timeout=10)
            if mutation == "create":
                response = create_entry_response(
                    mutation_session,
                    principal,
                    DiaryEntryCreate(
                        entry_date=current_diary_date(),
                        food_id=food_id,
                        quantity=1,
                    ),
                )
                assert response.food.id == food_id
            elif mutation == "update":
                assert entry_id is not None
                response = update_entry_response(
                    mutation_session,
                    principal,
                    entry_id,
                    DiaryEntryUpdate(quantity=2),
                )
                assert response.quantity == 2
                assert response.food.id == food_id
            else:
                assert entry_id is not None
                delete_entry(mutation_session, principal, entry_id)
            assert pending_delete.result(timeout=30) == 204

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM food WHERE id=:food"), {"food": food_id}
        ).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM diary_entry WHERE food_id=:food"), {"food": food_id}
        ).scalar_one() == 0
    engine.dispose()


@pytest.mark.migration
def test_concurrent_duplicate_food_delete_has_one_success_and_one_not_found() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(
        url,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"},
    )
    food_id = _add_current_food(engine, "Duplicate delete race")
    principal = PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL)
    barrier = Barrier(2)

    def concurrent_delete() -> int:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                delete_food(session, principal, food_id)
            except HTTPException as error:
                return error.status_code
            return 204

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(lambda _: concurrent_delete(), range(2)))

    assert results == [204, 404]
    engine.dispose()


@pytest.mark.migration
def test_food_delete_rolls_back_food_and_diary_cascade_when_database_rejects_delete() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(url)
    food_id = _add_current_food(engine, "Atomic delete rollback")
    principal = PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL)
    with Session(engine) as session:
        entry_id = create_entry(
            session,
            principal,
            DiaryEntryCreate(
                entry_date=current_diary_date(),
                food_id=food_id,
                quantity=1,
            ),
        ).id
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION test_reject_food_delete() RETURNS trigger LANGUAGE plpgsql "
                "AS $$ BEGIN RAISE EXCEPTION 'injected delete failure'; END $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER test_reject_food_delete BEFORE DELETE ON food "
                "FOR EACH ROW EXECUTE FUNCTION test_reject_food_delete()"
            )
        )
    try:
        with Session(engine) as session, pytest.raises(DBAPIError, match="injected delete failure"):
            delete_food(session, principal, food_id)
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM food WHERE id=:food"), {"food": food_id}
            ).scalar_one() == 1
            assert connection.execute(
                text("SELECT count(*) FROM diary_entry WHERE id=:entry"), {"entry": entry_id}
            ).scalar_one() == 1
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TRIGGER test_reject_food_delete ON food"))
            connection.execute(text("DROP FUNCTION test_reject_food_delete()"))
        engine.dispose()


@pytest.mark.migration
def test_food_delete_serializes_with_food_update_and_target_rebind_without_deleting_plan() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(
        url,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"},
    )
    food_id = _add_current_food(engine, "Food update and target race")
    principal = PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL)
    _write_current_target(engine, _current_target_write_request(80), "delete-race-current-plan")
    with Session(engine) as update_session:
        update_session.exec(
            select(Principal)
            .where(Principal.id == DEPLOYMENT_PRINCIPAL)
            .with_for_update()
        ).one()
        delete_started = Event()

        def concurrent_delete() -> None:
            delete_started.set()
            with Session(engine) as session:
                delete_food(session, principal, food_id)

        with ThreadPoolExecutor(max_workers=1) as executor:
            pending_delete = executor.submit(concurrent_delete)
            assert delete_started.wait(timeout=10)
            updated = update_food_response(
                update_session,
                principal,
                food_id,
                FoodUpdate(notes="serialized update"),
            )
            assert updated.notes == "serialized update"
            pending_delete.result(timeout=30)

    future_date = current_diary_date() + timedelta(days=1)
    rebound_food_id = _add_current_food(engine, "Target rebind race")
    with Session(engine) as session:
        create_entry(
            session,
            principal,
            DiaryEntryCreate(entry_date=future_date, food_id=rebound_food_id, quantity=1),
        )
    barrier = Barrier(2)

    def concurrent_target_write():
        barrier.wait(timeout=10)
        return _write_current_target(
            engine,
            _current_target_write_request(84, future_date),
            "delete-race-future-plan",
        )

    def concurrent_rebound_food_delete() -> None:
        barrier.wait(timeout=10)
        with Session(engine) as session:
            delete_food(session, principal, rebound_food_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        plan_future = executor.submit(concurrent_target_write)
        delete_future = executor.submit(concurrent_rebound_food_delete)
        plan_id, replayed = plan_future.result(timeout=30)
        delete_future.result(timeout=30)

    assert replayed is False
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM target_plan")).scalar_one() == 2
        assert connection.execute(
            text("SELECT revision FROM target_plan WHERE id=:plan"), {"plan": plan_id}
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT count(*) FROM food WHERE id IN (:food, :rebound_food)"),
            {"food": food_id, "rebound_food": rebound_food_id},
        ).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM diary_entry WHERE food_id IN (:food, :rebound_food)"),
            {"food": food_id, "rebound_food": rebound_food_id},
        ).scalar_one() == 0
    engine.dispose()


@pytest.mark.migration
def test_plan021_concurrent_same_operation_is_one_execution_and_one_replay() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(
        url,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"},
    )
    request = _current_target_write_request(82)
    barrier = Barrier(2)

    def concurrent_activate() -> tuple[str, bool]:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            response, replayed = write_target_plan(
                session,
                PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                request,
                "plan021-same-operation-race",
            )
            return str(response.plan.id), replayed

    executor = ThreadPoolExecutor(max_workers=2)
    try:
        futures = [executor.submit(concurrent_activate) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    assert {plan_id for plan_id, _ in results} == {results[0][0]}
    assert sorted(replayed for _, replayed in results) == [False, True]
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM target_plan")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM idempotency_record")).scalar_one() == 1
        assert (
            connection.execute(
                text(
                    "SELECT operation FROM idempotency_record "
                    "WHERE idempotency_key='plan021-same-operation-race'"
                )
            ).scalar_one()
            == "target_plan.write"
        )
    engine.dispose()


@pytest.mark.migration
def test_concurrent_write_key_reuse_with_different_payload_fails_closed() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(
        url,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"},
    )
    first_request = _current_target_write_request(82)
    conflicting_request = _current_target_write_request(
        84, current_diary_date() + timedelta(days=1)
    )
    shared_key = "target-plan-write-payload-race"
    start_barrier = Barrier(2)
    activation_commit_ready = Event()
    replacement_started = Event()

    def first_with_gated_commit() -> tuple[str, bool]:
        with Session(engine) as session:
            original_commit = session.commit

            def gated_commit() -> None:
                activation_commit_ready.set()
                assert replacement_started.wait(timeout=10)
                original_commit()

            session.commit = gated_commit
            start_barrier.wait(timeout=10)
            response, replayed = write_target_plan(
                session,
                PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                first_request,
                shared_key,
            )
            return str(response.plan.id), replayed

    def conflicting_after_first_reaches_commit() -> str:
        with Session(engine) as session:
            start_barrier.wait(timeout=10)
            assert activation_commit_ready.wait(timeout=10)
            replacement_started.set()
            try:
                write_target_plan(
                    session,
                    PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                    conflicting_request,
                    shared_key,
                )
            except TargetPlanError as error:
                return error.code
            return "created"

    executor = ThreadPoolExecutor(max_workers=2)
    try:
        first_future = executor.submit(first_with_gated_commit)
        conflicting_future = executor.submit(conflicting_after_first_reaches_commit)
        first_result = first_future.result(timeout=30)
        conflicting_result = conflicting_future.result(timeout=30)
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    assert first_result[1] is False
    assert conflicting_result == "IDEMPOTENCY_KEY_REUSED"
    assert _write_current_target(engine, first_request, shared_key) == (
        first_result[0],
        True,
    )
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM target_plan")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM idempotency_record")).scalar_one() == 1
        assert (
            connection.execute(
                text("SELECT operation FROM idempotency_record WHERE idempotency_key=:key"),
                {"key": shared_key},
            ).scalar_one()
            == "target_plan.write"
        )
    engine.dispose()


def _seed_plan009_food(url: str) -> tuple[UUID, UUID]:
    principal_id = uuid4()
    food_id = uuid4()
    engine = create_engine(url)
    with Session(engine) as session:
        session.add(Principal(id=principal_id))
        session.flush()
        session.execute(
            HISTORICAL_FOOD_TABLE.insert().values(
                id=food_id,
                created_by_principal_id=principal_id,
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
                created_at=PLAN009_TIMESTAMP,
                updated_at=PLAN009_TIMESTAMP,
            )
        )
        session.commit()
    engine.dispose()
    return principal_id, food_id


def _seed_plan023_diary_entry(url: str) -> tuple[UUID, UUID, UUID]:
    principal_id, food_id = _seed_plan009_food(url)
    entry_id = uuid4()
    engine = create_engine(url)
    with Session(engine) as session:
        session.execute(
            text(
                "INSERT INTO diary_entry "
                "(id,principal_id,entry_date,food_id,quantity,meal_type,nutrition_snapshot,"
                "target_plan_id,target_provenance,snapshot_schema_version,created_at) "
                "VALUES (:id,:principal_id,:entry_date,:food_id,1,'unspecified',"
                "CAST(:snapshot AS jsonb),NULL,'no_target_source',NULL,:created_at)"
            ),
            {
                "id": entry_id,
                "principal_id": principal_id,
                "entry_date": date(2026, 8, 4),
                "food_id": food_id,
                "snapshot": json.dumps({"schema_version": 3}),
                "created_at": PLAN009_TIMESTAMP,
            },
        )
        session.commit()
    engine.dispose()
    return principal_id, food_id, entry_id


def _plan023_constraint_names(url: str) -> set[str]:
    engine = create_engine(url)
    names = {
        constraint["name"] for constraint in inspect(engine).get_check_constraints("diary_entry")
    }
    engine.dispose()
    return names


def _plan023_quantity_text(url: str, entry_id: UUID) -> str:
    engine = create_engine(url)
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT quantity::text FROM diary_entry WHERE id = :id"),
            {"id": entry_id},
        ).scalar_one()
    engine.dispose()
    return value


def test_plan023_model_has_one_named_positive_finite_quantity_check() -> None:
    checks = [
        constraint
        for constraint in DiaryEntry.__table__.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name == PLAN023_CONSTRAINT
    ]

    assert len(checks) == 1
    expression = str(checks[0].sqltext)
    assert "quantity > 0" in expression
    for special in ("NaN", "Infinity", "-Infinity"):
        assert f"'{special}'" in expression


def test_plan023_offline_upgrade_renders_preflight_and_named_check() -> None:
    result = _run_alembic(
        "postgresql+psycopg://offline:offline@127.0.0.1:5432/mynutri_test_offline",
        "upgrade",
        f"{PLAN021_REVISION}:{PLAN023_REVISION}",
        "--sql",
    )

    assert "quantity <= 0 OR quantity::text IN" in result.stdout
    assert "ORDER BY id" in result.stdout
    assert "LIMIT 10" in result.stdout
    assert PLAN023_PREFLIGHT_ERROR in result.stdout
    assert PLAN023_PREFLIGHT_GUARD in result.stdout
    assert PLAN023_CONSTRAINT in result.stdout
    assert "UPDATE diary_entry" not in result.stdout
    assert "DELETE FROM diary_entry" not in result.stdout


@pytest.mark.migration
def test_plan023_fresh_valid_downgrade_and_populated_reupgrade() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", PLAN023_REVISION)

    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN023_REVISION
        )
    engine.dispose()
    assert PLAN023_CONSTRAINT in _plan023_constraint_names(url)

    _run_alembic(url, "downgrade", PLAN021_REVISION)
    assert PLAN023_CONSTRAINT not in _plan023_constraint_names(url)
    _, _, entry_id = _seed_plan023_diary_entry(url)
    before = _plan023_quantity_text(url, entry_id)

    _run_alembic(url, "upgrade", PLAN023_REVISION)

    assert _plan023_quantity_text(url, entry_id) == before == "1.000"
    assert PLAN023_CONSTRAINT in _plan023_constraint_names(url)


@pytest.mark.migration
def test_plan023_invalid_predecessor_rows_fail_closed_then_clean_fixture_upgrades() -> None:
    url = _database_url()
    for invalid in ("0", "-1", "NaN"):
        _reset_database(url)
        _run_alembic(url, "upgrade", PLAN021_REVISION)
        _, _, entry_id = _seed_plan023_diary_entry(url)
        engine = create_engine(url)
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE diary_entry SET quantity = CAST(:quantity AS numeric) WHERE id = :id"),
                {"quantity": invalid, "id": entry_id},
            )
        engine.dispose()
        before = _plan023_quantity_text(url, entry_id)

        result = _run_alembic(url, "upgrade", PLAN023_REVISION, check=False)
        output = result.stdout + result.stderr

        assert result.returncode != 0
        assert PLAN023_PREFLIGHT_ERROR in output
        assert PLAN023_PREFLIGHT_GUARD in output
        assert "invalid_count=1" in output
        assert str(entry_id) in output
        engine = create_engine(url)
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == PLAN021_REVISION
            )
        engine.dispose()
        assert PLAN023_CONSTRAINT not in _plan023_constraint_names(url)
        assert _plan023_quantity_text(url, entry_id) == before

        engine = create_engine(url)
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM diary_entry WHERE id = :id"),
                {"id": entry_id},
            )
        engine.dispose()
        _run_alembic(url, "upgrade", PLAN023_REVISION)
        assert PLAN023_CONSTRAINT in _plan023_constraint_names(url)

    for special in ("Infinity", "-Infinity"):
        _reset_database(url)
        _run_alembic(url, "upgrade", PLAN021_REVISION)
        _, _, entry_id = _seed_plan023_diary_entry(url)
        engine = create_engine(url)
        with pytest.raises(DBAPIError) as rejected:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE diary_entry SET quantity = CAST(:quantity AS numeric) "
                        "WHERE id = :id"
                    ),
                    {"quantity": special, "id": entry_id},
                )
        assert isinstance(rejected.value.orig, NumericValueOutOfRange)
        assert rejected.value.orig.sqlstate == "22003"
        engine.dispose()
        assert _plan023_quantity_text(url, entry_id) == "1.000"


def _assert_plan023_direct_write_rejected(error: DBAPIError, value: str) -> None:
    if value in {"Infinity", "-Infinity"}:
        assert isinstance(error.orig, NumericValueOutOfRange)
        assert error.orig.sqlstate == "22003"
        return
    assert isinstance(error.orig, CheckViolation)
    assert error.orig.sqlstate == "23514"
    assert error.orig.diag.constraint_name == PLAN023_CONSTRAINT


@pytest.mark.migration
def test_plan023_postgresql_direct_writes_enforce_positive_finite_quantity() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", PLAN023_REVISION)
    _, _, entry_id = _seed_plan023_diary_entry(url)
    engine = create_engine(url)

    for invalid in ("0", "-1", "NaN", "Infinity", "-Infinity"):
        inserted_id = uuid4()
        with pytest.raises(DBAPIError) as insert_rejected:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO diary_entry
                          (id, principal_id, entry_date, food_id, target_plan_id,
                           target_provenance, snapshot_schema_version, quantity,
                           meal_type, nutrition_snapshot, created_at)
                        SELECT :new_id, principal_id, entry_date, food_id, target_plan_id,
                               target_provenance, snapshot_schema_version,
                               CAST(:quantity AS numeric), meal_type,
                               nutrition_snapshot, created_at
                          FROM diary_entry
                         WHERE id = :source_id
                        """
                    ),
                    {"new_id": inserted_id, "source_id": entry_id, "quantity": invalid},
                )
        _assert_plan023_direct_write_rejected(insert_rejected.value, invalid)
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM diary_entry WHERE id = :id"),
                    {"id": inserted_id},
                ).scalar_one()
                == 0
            )

        with pytest.raises(DBAPIError) as update_rejected:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE diary_entry SET quantity = CAST(:quantity AS numeric) "
                        "WHERE id = :id"
                    ),
                    {"quantity": invalid, "id": entry_id},
                )
        _assert_plan023_direct_write_rejected(update_rejected.value, invalid)
        assert _plan023_quantity_text(url, entry_id) == "1.000"

    expected_positive_values = (
        Decimal("0.001"),
        Decimal("1.250"),
        Decimal("50.000"),
    )
    for expected in expected_positive_values:
        inserted_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO diary_entry
                      (id, principal_id, entry_date, food_id, target_plan_id,
                       target_provenance, snapshot_schema_version, quantity,
                       meal_type, nutrition_snapshot, created_at)
                    SELECT :new_id, principal_id, entry_date, food_id, target_plan_id,
                           target_provenance, snapshot_schema_version,
                           :quantity, meal_type, nutrition_snapshot, created_at
                      FROM diary_entry
                     WHERE id = :source_id
                    """
                ),
                {"new_id": inserted_id, "source_id": entry_id, "quantity": expected},
            )

        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT quantity FROM diary_entry WHERE id = :id"),
                {"id": inserted_id},
            ).scalar_one()
            assert isinstance(stored, Decimal)
            assert stored == expected
            assert connection.execute(
                text("SELECT quantity::text FROM diary_entry WHERE id = :id"),
                {"id": inserted_id},
            ).scalar_one() == format(expected, "f")
    engine.dispose()


def _assert_plan009_special_value_failure(
    error: DBAPIError,
    special: str,
    constraint_names: str | frozenset[str],
) -> None:
    if special == "NaN":
        approved_names = (
            frozenset({constraint_names}) if isinstance(constraint_names, str) else constraint_names
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

    # Target Plan 009 directly so later irreversible revisions cannot shadow its guard.
    result = _run_alembic(
        url,
        "upgrade",
        PLAN009_FINITE_NUTRIENTS_REVISION,
        check=False,
    )

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
    # Keep the round trip within Plan 009's historical boundary, below Plan 012.
    _run_alembic(url, "upgrade", PLAN009_FINITE_NUTRIENTS_REVISION)
    principal_id = DEPLOYMENT_PRINCIPAL
    food_id = identifiers["other"]
    engine = create_engine(url)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN009_FINITE_NUTRIENTS_REVISION
        )
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
            set(HISTORICAL_FOOD_GROUP_NUMERIC_COLUMNS),
        ),
    }
    for constraint_name, (table_name, expected_columns) in expected_constraint_metadata.items():
        constraint = constraints[constraint_name]
        assert constraint.convalidated is True
        assert constraint.table_name == table_name
        assert set(constraint.column_names) == expected_columns
        for special in ("NaN", "Infinity", "-Infinity"):
            assert constraint.definition.count(f"'{special}'::numeric") == len(expected_columns)

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
                    connection.execute(HISTORICAL_FOOD_TABLE.insert().values(**values))
            _assert_plan009_special_value_failure(
                rejected.value, special, "ck_food_numeric_values_finite"
            )
            with engine.connect() as connection:
                assert (
                    connection.execute(
                        text("SELECT count(*) FROM food WHERE id = :food"),
                        {"food": rejected_id},
                    ).scalar_one()
                    == 0
                )

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
                            f"UPDATE food SET {field} = CAST(:special AS numeric) WHERE id = :food"
                        ),
                        {"special": special, "food": food_id},
                    )
            _assert_plan009_special_value_failure(
                rejected.value, special, "ck_food_numeric_values_finite"
            )
            with engine.connect() as connection:
                assert (
                    connection.execute(
                        text(f"SELECT {field} FROM food WHERE id = :food"),
                        {"food": food_id},
                    ).one()[0]
                    == original
                )

    contribution_id = uuid4()
    with Session(engine) as session:
        session.execute(
            HISTORICAL_FOOD_GROUP_TABLE.insert().values(
                id=contribution_id,
                created_by_principal_id=principal_id,
                food_id=food_id,
                group_key="fruits",
                amount_per_100_basis=100,
                data_status="known",
                food_group_rules_version="1.0.0",
                created_at=PLAN009_TIMESTAMP,
                updated_at=PLAN009_TIMESTAMP,
            )
        )
        session.commit()
    for special in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(DBAPIError) as rejected:
            with engine.begin() as connection:
                connection.execute(
                    HISTORICAL_FOOD_GROUP_TABLE.insert().values(
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
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM food_group_contribution "
                        "WHERE food_id = :food AND group_key = 'vegetables'"
                    ),
                    {"food": food_id},
                ).scalar_one()
                == 0
            )
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
                text("SELECT amount_per_100_basis FROM food_group_contribution WHERE id = :id"),
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
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0014_v2_food_taxonomy"
        )
        during = connection.execute(
            text(
                "SELECT unit_amount, calories, protein_g, carb_g, fat_g, "
                "fiber_g, sodium_mg, vitamin_d_mcg, sugar_g "
                "FROM food WHERE id = :food"
            ),
            {"food": maximum_food_id},
        ).one()
    _run_alembic(url, "upgrade", PLAN009_FINITE_NUTRIENTS_REVISION)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN009_FINITE_NUTRIENTS_REVISION
        )
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


def test_plan012_offline_downgrade_fails_before_destructive_sql() -> None:
    result = _run_alembic(
        "postgresql+psycopg://offline:offline@127.0.0.1:5432/mynutri_test_offline",
        "downgrade",
        f"{PLAN012_GUARD_REVISION}:df46234d2a7e",
        "--sql",
        check=False,
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert PLAN012_DOWNGRADE_ERROR in output
    assert PLAN012_DOWNGRADE_GUARD in output
    assert PLAN021_DOWNGRADE_ERROR not in output
    assert PLAN021_DOWNGRADE_GUARD not in output
    assert "offline downgrade SQL is intentionally unavailable" in output
    assert "ALTER TABLE" not in result.stdout
    assert "DROP TABLE" not in result.stdout
    assert "UPDATE " not in result.stdout
    assert "DELETE " not in result.stdout
    assert "INSERT " not in result.stdout


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
) -> None:
    before_audit = _plan012_audit_signature(url)
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN012_GUARD_REVISION
        )
    engine.dispose()
    result = _run_alembic(url, "downgrade", "0013_v2_shared_food_catalog", check=False)
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert PLAN012_DOWNGRADE_ERROR in output
    assert PLAN012_DOWNGRADE_GUARD in output
    assert PLAN021_DOWNGRADE_ERROR not in output
    assert PLAN021_DOWNGRADE_GUARD not in output
    assert PLAN012_IRREVERSIBLE_REASON in output
    assert "Running downgrade 0014_v2_food_taxonomy" not in output
    assert "NotNullViolation" not in output
    engine = create_engine(url)
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN012_GUARD_REVISION
        )
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    column_names = {column["name"] for column in inspector.get_columns("food")}
    engine.dispose()
    assert "food_category_key" in column_names
    assert "category" not in column_names
    assert _plan012_food_signature(url) == before_food
    assert _plan012_audit_signature(url) == before_audit
    assert _plan012_schema_signature(url) == before_schema

    # The historical assertions above must run at the frozen Plan 012 boundary.
    # Restore only to the preserved historical boundary. The callers still verify
    # the frozen Plan 012 schema after this helper returns.
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)


@pytest.mark.migration
def test_plan012_empty_database_blocks_before_frozen_0014_downgrade() -> None:
    url = _database_url()
    _prepare_plan012_0013_foods(url, ())
    _run_alembic(url, "upgrade", PLAN012_GUARD_REVISION)

    assert _plan012_food_signature(url) == ()
    assert _plan012_audit_signature(url) == ()
    _assert_plan012_guard_failure(
        url,
        before_food=(),
        before_schema=_plan012_schema_signature(url),
    )


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
    _run_alembic(url, "upgrade", PLAN012_GUARD_REVISION)
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
def test_plan012_non_null_legacy_ledger_blocks_irreversible_boundary() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, PLAN012_NON_NULL_LEGACY_CATEGORY_KEYS)

    _run_alembic(url, "upgrade", PLAN012_GUARD_REVISION)
    v2_before = _plan012_food_signature(url)
    v2_schema_before = _plan012_schema_signature(url)
    audit_before = _plan012_audit_signature(url)
    actual_by_id = {row[0]: row[1:] for row in v2_before}
    assert actual_by_id == {
        food_id: _plan012_expected_tuple(legacy_key) for legacy_key, food_id in identifiers.items()
    }

    _assert_plan012_guard_failure(
        url,
        before_food=v2_before,
        before_schema=v2_schema_before,
    )
    assert _plan012_food_signature(url) == v2_before
    assert _plan012_audit_signature(url) == audit_before


@pytest.mark.migration
def test_plan012_legacy_null_origin_blocks_before_frozen_0014_downgrade() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, (None,))
    _run_alembic(url, "upgrade", PLAN012_GUARD_REVISION)

    before_food = _plan012_food_signature(url)
    before_schema = _plan012_schema_signature(url)
    assert before_food == ((identifiers[None], *_plan012_expected_tuple(None)),)
    engine = create_engine(url)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM food_taxonomy_v2_migration_audit "
                    "WHERE legacy_primary_category_key IS NULL"
                )
            ).scalar_one()
            == 1
        )
    engine.dispose()

    _assert_plan012_guard_failure(
        url,
        before_food=before_food,
        before_schema=before_schema,
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
    _run_alembic(url, "upgrade", PLAN012_GUARD_REVISION)
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
def test_plan012_snapshot_v3_baseline_condition_blocks_at_historical_boundary() -> None:
    url = _database_url()
    identifiers = _prepare_plan012_0013_foods(url, ("other",))
    _run_alembic(url, "upgrade", PLAN012_GUARD_REVISION)
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


@pytest.mark.migration
def test_plan032_empty_downgrade_and_reupgrade_are_reversible() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)
    _run_alembic(url, "downgrade", PLAN031_REVISION)
    engine = create_engine(url)
    try:
        assert "nutrition_analysis" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)


@pytest.mark.migration
def test_plan032_populated_downgrade_refuses_without_deleting_history() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)
    principal_id = uuid4()
    analysis_id = uuid4()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,auth_user_id,role,status,created_at,updated_at) "
                "VALUES (:id,:auth,'user','active',now(),now())"
            ),
            {"id": principal_id, "auth": uuid4()},
        )
        connection.execute(
            text(
                "INSERT INTO nutrition_analysis "
                "(id,principal_id,as_of_diary_date,calendar_timezone,interface_version,created_at,updated_at) "
                "VALUES (:id,:principal,'2026-08-17','Asia/Riyadh',1,now(),now())"
            ),
            {"id": analysis_id, "principal": principal_id},
        )
    result = _run_alembic(url, "downgrade", PLAN031_REVISION, check=False)
    assert result.returncode != 0
    assert NOVA_RETIREMENT_DOWNGRADE_ERROR in result.stdout + result.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM nutrition_analysis")).scalar_one() == 1
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == NOVA_RETIREMENT_REVISION
        )
    engine.dispose()


@pytest.mark.migration
def test_plan033_empty_downgrade_and_reupgrade_are_reversible() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)
    _run_alembic(url, "downgrade", PLAN032_REVISION)
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "weekly_priority_recommendation" not in tables
        assert "behavior_goal" not in tables
    finally:
        engine.dispose()
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)


@pytest.mark.migration
def test_plan033_populated_downgrade_refuses_without_deleting_history(
    database_restored_to_current_head: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)
    principal_id, analysis_id, revision_id, recommendation_id = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO principal (id,auth_user_id,role,status,created_at,updated_at) "
                "VALUES (:id,:auth,'user','active',now(),now())"
            ),
            {"id": principal_id, "auth": uuid4()},
        )
        connection.execute(
            text(
                "INSERT INTO nutrition_analysis "
                "(id,principal_id,as_of_diary_date,calendar_timezone,interface_version,created_at,updated_at) "
                "VALUES (:id,:principal,'2026-08-17','Asia/Riyadh',1,now(),now())"
            ),
            {"id": analysis_id, "principal": principal_id},
        )
        connection.execute(
            text(
                "INSERT INTO nutrition_analysis_revision "
                "(id,analysis_id,principal_id,revision,period_start,period_end,previous_period_start,"
                "previous_period_end,analysis_rules_version,source_versions,source_input_hash,content_hash,"
                "complete_day_count,previous_complete_day_count,result_status,analysis_document,generated_at,finalized_at) "
                "VALUES (:revision,:analysis,:principal,1,'2026-08-11','2026-08-17','2026-08-04','2026-08-10',"
                "'w3-analysis-1.1.0','{}',:source_hash,:content_hash,4,4,'available','{}',now(),now())"
            ),
            {
                "revision": revision_id,
                "analysis": analysis_id,
                "principal": principal_id,
                "source_hash": "1" * 64,
                "content_hash": "2" * 64,
            },
        )
        connection.execute(
            text(
                "INSERT INTO weekly_priority_recommendation "
                "(id,principal_id,source_analysis_revision_id,source_analysis_id,source_analysis_revision,"
                "schema_version,period_start,period_end,as_of_diary_date,evaluation_diary_date,"
                "evaluation_mode,status,rules_version,copy_version,"
                "analysis_rules_version,source_versions,result_document,input_digest,content_hash,generated_at,expires_at) "
                "VALUES (:id,:principal,:revision,:analysis,1,1,'2026-08-11','2026-08-17','2026-08-17',"
                "'2026-08-17','live',"
                "'none','w3-priority-1.1.0','w3-priority-ar-1.1.0','w3-analysis-1.1.0','{}','{}',"
                ":input_hash,:content_hash,now(),now()+interval '36 hours')"
            ),
            {
                "id": recommendation_id,
                "principal": principal_id,
                "revision": revision_id,
                "analysis": analysis_id,
                "input_hash": "3" * 64,
                "content_hash": "4" * 64,
            },
        )
    result = _run_alembic(url, "downgrade", PLAN032_REVISION, check=False)
    assert result.returncode != 0
    assert NOVA_RETIREMENT_DOWNGRADE_ERROR in result.stdout + result.stderr
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM weekly_priority_recommendation")
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == NOVA_RETIREMENT_REVISION
        )
    engine.dispose()


def _assert_food_simplification_failure_left_source_schema(
    engine, entry_id: UUID
) -> None:
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            NOVA_RETIREMENT_REVISION
        )
        assert connection.execute(
            text("SELECT count(*) FROM diary_entry WHERE id=:id"), {"id": entry_id}
        ).scalar_one() == 1
    diary_columns = {column["name"] for column in inspector.get_columns("diary_entry")}
    assert "nutrition_snapshot" in diary_columns
    assert "recorded_unit_basis" not in diary_columns


@pytest.mark.migration
@pytest.mark.parametrize("reference_state", ["null", "orphan"])
def test_food_simplification_rejects_missing_diary_food_reference_atomically(
    database_restored_to_current_head: str,
    reference_state: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", "0014_v2_food_taxonomy")
    principal_id, food_id = _seed_plan009_food(url)
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)
    entry_id = uuid4()
    missing_food_id = None if reference_state == "null" else uuid4()
    snapshot = {
        "schema_version": 4,
        "captured_unit": {
            "default_unit_type": "serving",
            "unit_amount": 100,
            "unit_basis": "g",
        },
    }
    engine = create_engine(url)
    with engine.begin() as connection:
        if reference_state == "orphan":
            connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(
            text(
                "INSERT INTO diary_entry "
                "(id,principal_id,entry_date,food_id,quantity,meal_type,nutrition_snapshot,"
                "target_plan_id,target_provenance,snapshot_schema_version,created_at) VALUES "
                "(:id,:principal,'2026-09-01',:food,1,'unspecified',CAST(:snapshot AS jsonb),"
                "NULL,'no_target_source',4,:created_at)"
            ),
            {
                "id": entry_id,
                "principal": principal_id,
                "food": missing_food_id,
                "snapshot": json.dumps(snapshot),
                "created_at": PLAN009_TIMESTAMP,
            },
        )
        if reference_state == "orphan":
            connection.execute(text("SET LOCAL session_replication_role = origin"))

    result = _run_alembic(url, "upgrade", FOOD_SIMPLIFICATION_REVISION, check=False)

    assert result.returncode != 0
    assert "FOOD_SIMPLIFICATION_ORPHANED_DIARY_FOOD_REFERENCE" in (
        result.stdout + result.stderr
    )
    _assert_food_simplification_failure_left_source_schema(engine, entry_id)
    with engine.connect() as connection:
        actual_food_id = connection.execute(
            text("SELECT food_id FROM diary_entry WHERE id=:id"), {"id": entry_id}
        ).scalar_one_or_none()
    assert actual_food_id == missing_food_id
    assert food_id != missing_food_id
    engine.dispose()


@pytest.mark.migration
def test_food_simplification_rejects_ambiguous_diary_measurement_atomically(
    database_restored_to_current_head: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", "0014_v2_food_taxonomy")
    principal_id, food_id = _seed_plan009_food(url)
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)
    entry_id = uuid4()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO diary_entry "
                "(id,principal_id,entry_date,food_id,quantity,meal_type,nutrition_snapshot,"
                "target_plan_id,target_provenance,snapshot_schema_version,created_at) VALUES "
                "(:id,:principal,'2026-09-01',:food,1,'unspecified',"
                "CAST(:snapshot AS jsonb),NULL,'no_target_source',4,:created_at)"
            ),
            {
                "id": entry_id,
                "principal": principal_id,
                "food": food_id,
                "snapshot": json.dumps({"schema_version": 4}),
                "created_at": PLAN009_TIMESTAMP,
            },
        )

    result = _run_alembic(url, "upgrade", FOOD_SIMPLIFICATION_REVISION, check=False)

    assert result.returncode != 0
    assert "FOOD_SIMPLIFICATION_DIARY_MEASUREMENT_BACKFILL_REQUIRED" in (
        result.stdout + result.stderr
    )
    _assert_food_simplification_failure_left_source_schema(engine, entry_id)
    engine.dispose()


@pytest.mark.migration
def test_food_simplification_rejects_legacy_diary_food_dimension_mismatch_atomically(
    database_restored_to_current_head: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", "0014_v2_food_taxonomy")
    principal_id, food_id = _seed_plan009_food(url)
    _run_alembic(url, "upgrade", NOVA_RETIREMENT_REVISION)
    entry_id = uuid4()
    snapshot = {
        "schema_version": 4,
        "captured_unit": {
            "default_unit_type": "serving",
            "unit_amount": 100,
            "unit_basis": "g",
        },
        "versions": {
            "nutrition_registry_version": "3.0.0",
            "snapshot_schema_version": 4,
        },
    }
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO diary_entry
                  (id,principal_id,entry_date,food_id,quantity,meal_type,nutrition_snapshot,
                   target_plan_id,target_provenance,snapshot_schema_version,created_at)
                VALUES
                  (:id,:principal,'2026-09-01',:food,1,'unspecified',CAST(:snapshot AS jsonb),
                   NULL,'no_target_source',4,:created_at)
                """
            ),
            {
                "id": entry_id,
                "principal": principal_id,
                "food": food_id,
                "snapshot": json.dumps(snapshot),
                "created_at": PLAN009_TIMESTAMP,
            },
        )
        connection.execute(
            text("UPDATE food SET nutrition_basis='per_100ml',unit_basis='ml' WHERE id=:id"),
            {"id": food_id},
        )

    result = _run_alembic(url, "upgrade", FOOD_SIMPLIFICATION_REVISION, check=False)

    assert result.returncode != 0
    assert (
        "FOOD_SIMPLIFICATION_DIARY_FOOD_DIMENSION_RECONCILIATION_REQUIRED"
        in result.stdout + result.stderr
    )
    _assert_food_simplification_failure_left_source_schema(engine, entry_id)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT nutrition_snapshot->>'schema_version' FROM diary_entry WHERE id=:id"),
                {"id": entry_id},
            ).scalar_one()
            == "4"
        )
    engine.dispose()


@pytest.mark.migration
def test_food_simplification_maps_ambiguous_dairy_primary_to_other(
    database_restored_to_current_head: str,
) -> None:
    url = database_restored_to_current_head
    _reset_database(url)
    _run_alembic(url, "upgrade", "0014_v2_food_taxonomy")
    _, food_id = _seed_plan009_food(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE food SET food_category_key='dairy_fortified_alternatives' WHERE id=:id"),
            {"id": food_id},
        )
    engine.dispose()
    _run_alembic(url, "upgrade", FOOD_SIMPLIFICATION_REVISION)

    engine = create_engine(url)
    with engine.connect() as connection:
        mapped = connection.execute(
            text("SELECT primary_category,subcategory FROM food WHERE id=:id"),
            {"id": food_id},
        ).one()
    engine.dispose()

    assert tuple(mapped) == ("other", "other")
