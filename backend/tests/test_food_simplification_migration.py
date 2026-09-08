from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from app.nutrition_rules.registry import FOOD_TAXONOMY


BACKEND_ROOT = Path(__file__).parents[1]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "f47a2c9d6e13_retire_food_and_analysis_features.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("food_simplification_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_food_simplification_migration_has_approved_topology_and_taxonomy() -> None:
    migration = _load_migration()

    assert migration.revision == "f47a2c9d6e13"
    assert migration.down_revision == "8a91c4e7d2f6"
    assert migration.FOOD_TAXONOMY == {
        primary["key"]: tuple(key for key, _label in primary["subcategories"])
        for primary in FOOD_TAXONOMY
    }


def test_food_simplification_offline_sql_contains_current_truth_contract() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "f47a2c9d6e13", "--sql"],
        cwd=BACKEND_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    sql = result.stdout

    for required_fragment in (
        "ALTER TABLE food ADD COLUMN primary_category TEXT",
        "ALTER TABLE food ADD COLUMN subcategory TEXT",
        "ALTER TABLE food ADD COLUMN nutrition_data_source TEXT",
        "ALTER TABLE diary_entry ADD COLUMN recorded_unit_type TEXT",
        "ALTER TABLE diary_entry ADD COLUMN recorded_unit_amount NUMERIC(10, 4)",
        "ALTER TABLE diary_entry ALTER COLUMN food_id SET NOT NULL",
        "REFERENCES food (id) ON DELETE RESTRICT",
        "DROP TABLE food_group_contribution CASCADE",
        "DROP TABLE food_analytical_trait CASCADE",
        "DROP TABLE nutrition_analysis CASCADE",
        "DROP TABLE weekly_priority_recommendation CASCADE",
        "DROP SCHEMA nova_retirement CASCADE",
    ):
        assert required_fragment in sql

    for retired_column in (
        "nutrition_snapshot",
        "snapshot_schema_version",
        "food_category_key",
        "grain_type",
        "baked_good_type",
        "grain_starch_type",
        "taxonomy_review_required",
        "food_kind",
        "group_data_status",
        "group_data_completeness",
        "nova_classification",
        "nova_review_status",
    ):
        assert f"DROP COLUMN {retired_column}" in sql

    assert "Snapshot V5" not in sql
    assert "snapshot_schema_version = 5" not in sql


def test_food_simplification_downgrade_fails_closed_before_sql_generation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "downgrade",
            "f47a2c9d6e13:8a91c4e7d2f6",
            "--sql",
        ],
        cwd=BACKEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "FOOD_SIMPLIFICATION_RETIREMENT_DOWNGRADE_BLOCKED" in result.stdout + result.stderr
    assert "offline downgrade SQL is intentionally unavailable" in result.stdout + result.stderr
