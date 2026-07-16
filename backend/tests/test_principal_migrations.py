from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

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
def test_fresh_postgresql_upgrade_has_one_head_and_owner_contract() -> None:
    url = _database_url()
    _reset_database(url)
    _run_alembic(url, "upgrade", "head")

    engine = create_engine(url)
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0006_principal_contract"
        )
    assert "principal" in inspector.get_table_names()
    for table in ("profile", "food", "diary_entry"):
        owner = next(column for column in inspector.get_columns(table) if column["name"] == "principal_id")
        assert owner["nullable"] is False
    profile_uniques = {tuple(item["column_names"]) for item in inspector.get_unique_constraints("profile")}
    assert ("principal_id",) in profile_uniques
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
            text("INSERT INTO principal (id, status, created_at, updated_at) VALUES (:id, 'active', now(), now())"),
            {"id": DEPLOYMENT_PRINCIPAL},
        )
    _run_alembic(url, "upgrade", "head")

    with engine.connect() as connection:
        for table in ("profile", "food", "diary_entry"):
            assert connection.execute(
                text(f"SELECT count(*) FROM {table} WHERE principal_id = :id"),
                {"id": DEPLOYMENT_PRINCIPAL},
            ).scalar_one() == 1
        snapshot_after = connection.execute(
            text("SELECT nutrition_snapshot::text FROM diary_entry WHERE id = :id"),
            {"id": identifiers["diary"]},
        ).scalar_one()
        assert snapshot_after == snapshot_before

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
                text(
                    "UPDATE diary_entry SET principal_id = :other WHERE id = :entry_id"
                ),
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
        assert connection.execute(
            text("SELECT count(*) FROM profile WHERE principal_id IS NOT NULL")
        ).scalar_one() == 0
    engine.dispose()

    cleanup_engine = create_engine(url)
    with cleanup_engine.begin() as connection:
        connection.execute(text("DELETE FROM principal WHERE id = :id"), {"id": other_principal})
    cleanup_engine.dispose()
    _run_alembic(url, "upgrade", "head")
