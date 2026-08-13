from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from threading import Barrier, Event
from uuid import UUID, uuid4

import pytest
from psycopg.errors import CheckViolation, NumericValueOutOfRange
from sqlalchemy import CheckConstraint, Numeric, String, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import SQLModel, Session

from app.core.auth import PrincipalContext
from app.models import (
    FOOD_GROUP_NUMERIC_COLUMNS,
    FOOD_NUMERIC_COLUMNS,
    DefaultUnitType,
    DiaryEntry,
    Food,
    FoodGroupContribution,
    NutritionBasis,
    Principal,
    UnitBasis,
)
from app.schemas import (
    ProfilePreview,
    TargetPlanActivationRequest,
    TargetPlanReplacementRequest,
)
from app.services.profile import to_target_response
from app.services.target_plans import TargetPlanError, activate_plan

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
    "df46234d2a7e_constrain_finite_food_nutrients.py": "70767434911230795129b4702f8d4bf2e9a4add9dcf1607c3fa648dfebdd0674",
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
PLAN023_CONSTRAINT = "ck_diary_entry_quantity_positive_finite"
PLAN023_PREFLIGHT_ERROR = "PLAN023_DIARY_QUANTITY_PREFLIGHT_BLOCKED"
PLAN023_PREFLIGHT_GUARD = "plan023_diary_quantity_positive_finite_preflight"
PLAN021_DOWNGRADE_ERROR = "PLAN021_TARGET_PLAN_IDEMPOTENCY_DOWNGRADE_BLOCKED"
PLAN021_DOWNGRADE_GUARD = "plan021_target_plan_idempotency_downgrade_guard"
AUTHORITATIVE_HISTORICAL_CHECKS = {
    "profile": (
        "ck_profile_cut_intensity",
        "cut_intensity IN (0.150,0.200,0.250)",
    ),
    "legacy_target_transition_snapshots": (
        "ck_legacy_transition_document_shape",
        "jsonb_typeof(legacy_target_document)='object' AND "
        "legacy_target_document->>'schema_version'='1' AND "
        "legacy_target_document->>'source'='legacy_unversioned_transition' AND "
        "jsonb_typeof(legacy_target_document->'captured_profile_inputs')='object' AND "
        "jsonb_typeof(legacy_target_document->'resolved_targets')='object'",
    ),
    "diary_entry": (
        "ck_diary_entry_versioned_shape",
        "snapshot_schema_version IS NULL OR "
        "(jsonb_typeof(nutrition_snapshot)='object' AND "
        "nutrition_snapshot->>'schema_version'=snapshot_schema_version::text)",
    ),
}
POSTGRESQL_AUTHORITATIVE_CHECK_DEFINITIONS = {
    "ck_diary_entry_versioned_shape": (
        "CHECK (snapshot_schema_version IS NULL OR "
        "jsonb_typeof(nutrition_snapshot) = 'object'::text AND "
        "(nutrition_snapshot ->> 'schema_version'::text) = "
        "snapshot_schema_version::text)"
    ),
    "ck_legacy_transition_document_shape": (
        "CHECK (jsonb_typeof(legacy_target_document) = 'object'::text AND "
        "(legacy_target_document ->> 'schema_version'::text) = '1'::text AND "
        "(legacy_target_document ->> 'source'::text) = "
        "'legacy_unversioned_transition'::text AND "
        "jsonb_typeof(legacy_target_document -> "
        "'captured_profile_inputs'::text) = 'object'::text AND "
        "jsonb_typeof(legacy_target_document -> "
        "'resolved_targets'::text) = 'object'::text)"
    ),
    "ck_profile_cut_intensity": (
        "CHECK (cut_intensity = ANY (ARRAY[0.150, 0.200, 0.250]))"
    ),
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


def _normalized_revision_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _assert_immutable_revision_hashes(versions: Path) -> None:
    revision_files = {path.name for path in versions.glob("*.py")}
    assert revision_files == set(BASELINE_HASHES)
    actual = {
        name: _normalized_revision_hash(versions / name)
        for name in BASELINE_HASHES
    }
    assert actual == BASELINE_HASHES


@pytest.mark.migration
def test_immutable_baseline_revision_hashes() -> None:
    versions = Path(__file__).parents[1] / "alembic" / "versions"
    _assert_immutable_revision_hashes(versions)


@pytest.mark.migration
def test_immutable_baseline_revision_hashes_detect_mutation(tmp_path: Path) -> None:
    versions = Path(__file__).parents[1] / "alembic" / "versions"
    copied_versions = tmp_path / "versions"
    shutil.copytree(versions, copied_versions)
    latest = copied_versions / "9f2a1b6c3d05_plan025_admin_diary_order_index.py"
    latest.write_bytes(latest.read_bytes() + b"\n# mutation probe\n")

    with pytest.raises(AssertionError):
        _assert_immutable_revision_hashes(copied_versions)


@pytest.mark.migration
def test_authoritative_historical_checks_are_in_metadata_and_sqlite_safe() -> None:
    for table_name, (constraint_name, expected_expression) in (
        AUTHORITATIVE_HISTORICAL_CHECKS.items()
    ):
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
            constraint["name"]
            for constraint in sqlite_inspector.get_check_constraints(table_name)
        ]
        for table_name in AUTHORITATIVE_HISTORICAL_CHECKS
    }

    assert sqlite_checks["profile"].count("ck_profile_cut_intensity") == 1
    assert "ck_legacy_transition_document_shape" not in sqlite_checks[
        "legacy_target_transition_snapshots"
    ]
    assert "ck_diary_entry_versioned_shape" not in sqlite_checks["diary_entry"]

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
def test_fresh_postgresql_upgrade_has_one_head_and_wave1_food_contract() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")

    engine = create_engine(url)
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            PLAN025_REVISION
        )
        authoritative_checks = connection.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid, true) "
                "FROM pg_constraint "
                "WHERE conname IN "
                "('ck_diary_entry_versioned_shape', "
                "'ck_legacy_transition_document_shape', "
                "'ck_profile_cut_intensity') "
                "ORDER BY conname"
            )
        ).all()
    assert len(authoritative_checks) == len(POSTGRESQL_AUTHORITATIVE_CHECK_DEFINITIONS)
    assert {
        name: _normalized_check_expression(definition)
        for name, definition in authoritative_checks
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

    check_result = _run_alembic(url, "check")
    check_output = check_result.stdout + check_result.stderr
    assert "alembic.autogenerate.checkconstraint_byname" in check_output
    assert "No new upgrade operations detected." in check_output


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


def _plan021_activation_request(weight: float) -> TargetPlanActivationRequest:
    draft = _plan021_draft(weight)
    preview = to_target_response(draft)
    return TargetPlanActivationRequest(
        **draft.model_dump(),
        confirmed=True,
        expected_preview_hash=preview.preview_hash,
    )


def _plan021_replacement_request(weight: float) -> TargetPlanReplacementRequest:
    draft = _plan021_draft(weight)
    preview = to_target_response(draft)
    return TargetPlanReplacementRequest(
        **draft.model_dump(),
        replace_confirmed=True,
        expected_preview_hash=preview.preview_hash,
    )


def _plan021_activate(
    engine,
    request: TargetPlanActivationRequest | TargetPlanReplacementRequest,
    key: str,
    *,
    replace_pending: bool = False,
) -> tuple[str, bool]:
    with Session(engine) as session:
        response, replayed = activate_plan(
            session,
            PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
            request,
            key,
            replace_pending=replace_pending,
        )
        return str(response.plan.id), replayed


def _plan021_schema_signature(url: str) -> tuple[frozenset[str], ...]:
    engine = create_engine(url)
    inspector = inspect(engine)
    target_uniques = frozenset(
        constraint["name"]
        for constraint in inspector.get_unique_constraints("target_plan")
    )
    ledger_uniques = frozenset(
        constraint["name"]
        for constraint in inspector.get_unique_constraints("idempotency_record")
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
    assert {"uq_target_plan_one_active", "uq_target_plan_one_scheduled"}.issubset(
        target_indexes
    )
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
    plan_id, replayed = _plan021_activate(
        engine,
        _plan021_activation_request(82),
        "plan021-populated-upgrade",
    )
    engine.dispose()
    assert replayed is False
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
    _plan021_activate(
        engine,
        _plan021_activation_request(82),
        "plan021-single-operation",
    )
    engine.dispose()
    before = _plan021_data_signature(url)

    _run_alembic(url, "downgrade", "5294eff9a956")

    engine = create_engine(url)
    inspector = inspect(engine)
    target_uniques = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("target_plan")
    }
    ledger_uniques = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("idempotency_record")
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
    activation_id, activation_replayed = _plan021_activate(
        engine,
        _plan021_activation_request(82),
        shared_key,
    )
    replacement_id, replacement_replayed = _plan021_activate(
        engine,
        _plan021_replacement_request(84),
        shared_key,
        replace_pending=True,
    )
    engine.dispose()
    assert activation_replayed is replacement_replayed is False
    assert activation_id != replacement_id
    before_data = _plan021_data_signature(url)
    before_schema = _plan021_schema_signature(url)
    assert len(before_data[0]) == 2
    assert {
        (record[0], record[1], record[4]) for record in before_data[1]
    } == {
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
    assert "Lossy downgrade of transition snapshots is prohibited." in downgrade.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            TRANSITION_SNAPSHOT_REVISION
        )
        assert connection.execute(
            text(
                "SELECT transition_date FROM legacy_target_transition_snapshots WHERE id=:id"
            ),
            {"id": snapshot_id},
        ).scalar_one() == date(2026, 7, 16)
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
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
        assert connection.execute(
            text("SELECT nutrition_snapshot::text FROM diary_entry WHERE id=:id"),
            {"id": entry_id},
        ).scalar_one() == before_delete
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
    request = _plan021_activation_request(82)
    barrier = Barrier(2)

    def concurrent_activate() -> tuple[str, bool]:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            response, replayed = activate_plan(
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
        assert connection.execute(
            text(
                "SELECT operation FROM idempotency_record "
                "WHERE idempotency_key='plan021-same-operation-race'"
            )
        ).scalar_one() == "target_plan.activate"
    engine.dispose()


@pytest.mark.migration
def test_plan021_concurrent_cross_operation_sessions_reuse_visible_key() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")
    _seed_plan021_profile(url)
    engine = create_engine(
        url,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"},
    )
    activation_request = _plan021_activation_request(82)
    replacement_request = _plan021_replacement_request(84)
    shared_key = "plan021-cross-operation-race"
    start_barrier = Barrier(2)
    activation_commit_ready = Event()
    replacement_started = Event()

    def activate_with_gated_commit() -> tuple[str, bool]:
        with Session(engine) as session:
            original_commit = session.commit

            def gated_commit() -> None:
                activation_commit_ready.set()
                assert replacement_started.wait(timeout=10)
                original_commit()

            session.commit = gated_commit
            start_barrier.wait(timeout=10)
            response, replayed = activate_plan(
                session,
                PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                activation_request,
                shared_key,
            )
            return str(response.plan.id), replayed

    def replace_after_activation_reaches_commit() -> tuple[str, bool]:
        with Session(engine) as session:
            start_barrier.wait(timeout=10)
            assert activation_commit_ready.wait(timeout=10)
            replacement_started.set()
            response, replayed = activate_plan(
                session,
                PrincipalContext(principal_id=DEPLOYMENT_PRINCIPAL),
                replacement_request,
                shared_key,
                replace_pending=True,
            )
            return str(response.plan.id), replayed

    executor = ThreadPoolExecutor(max_workers=2)
    try:
        activation_future = executor.submit(activate_with_gated_commit)
        replacement_future = executor.submit(replace_after_activation_reaches_commit)
        activation_result = activation_future.result(timeout=30)
        replacement_result = replacement_future.result(timeout=30)
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    assert activation_result[1] is replacement_result[1] is False
    assert activation_result[0] != replacement_result[0]
    assert _plan021_activate(engine, activation_request, shared_key) == (
        activation_result[0],
        True,
    )
    assert _plan021_activate(
        engine,
        replacement_request,
        shared_key,
        replace_pending=True,
    ) == (replacement_result[0], True)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM target_plan")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM idempotency_record")).scalar_one() == 2
        assert set(
            connection.execute(
                text(
                    "SELECT operation FROM idempotency_record "
                    "WHERE idempotency_key=:key"
                ),
                {"key": shared_key},
            ).scalars()
        ) == {"target_plan.activate", "target_plan.replace"}
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


def _seed_plan023_diary_entry(url: str) -> tuple[UUID, UUID, UUID]:
    principal_id, food_id = _seed_plan009_food(url)
    entry_id = uuid4()
    engine = create_engine(url)
    with Session(engine) as session:
        session.add(
            DiaryEntry(
                id=entry_id,
                principal_id=principal_id,
                entry_date=date(2026, 8, 4),
                food_id=food_id,
                quantity=1,
                nutrition_snapshot={"schema_version": 3},
            )
        )
        session.commit()
    engine.dispose()
    return principal_id, food_id, entry_id


def _plan023_constraint_names(url: str) -> set[str]:
    engine = create_engine(url)
    names = {
        constraint["name"]
        for constraint in inspect(engine).get_check_constraints("diary_entry")
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
        if isinstance(constraint, CheckConstraint)
        and constraint.name == PLAN023_CONSTRAINT
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
                text(
                    "UPDATE diary_entry SET quantity = CAST(:quantity AS numeric) "
                    "WHERE id = :id"
                ),
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
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == PLAN021_REVISION
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
            assert connection.execute(
                text("SELECT count(*) FROM diary_entry WHERE id = :id"),
                {"id": inserted_id},
            ).scalar_one() == 0

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

        with Session(engine) as session:
            stored = session.get(DiaryEntry, inserted_id)
            assert stored is not None
            assert isinstance(stored.quantity, Decimal)
            assert stored.quantity == expected
        with engine.connect() as connection:
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
    result = _run_alembic(
        url, "downgrade", "0013_v2_shared_food_catalog", check=False
    )
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
    # Restore the shared disposable database only after that proof is complete so
    # the repository-level model-drift gate starts from the current schema.
    _run_alembic(url, "upgrade", "head")


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
        food_id: _plan012_expected_tuple(legacy_key)
        for legacy_key, food_id in identifiers.items()
    }

    _assert_plan012_guard_failure(
        url,
        before_food=v2_before,
        before_schema=v2_schema_before,
    )
    assert _plan012_food_signature(url) == v2_before
    assert _plan012_schema_signature(url) == v2_schema_before
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
