from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / (
    "d9f64a1c3e58_unify_food_catalog_and_cascade_diary_deletion.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_food_catalog_unification_migration_is_forward_only_and_dependency_safe() -> None:
    source = migration_source()

    assert 'revision: str = "d9f64a1c3e58"' in source
    assert 'down_revision: str | None = "c8e53f0b2d47"' in source
    assert "LOCK TABLE food IN ACCESS EXCLUSIVE MODE" in source
    assert "LOCK TABLE diary_entry IN ACCESS EXCLUSIVE MODE" in source
    assert "FOOD_CATALOG_SIMPLIFICATION_PREFLIGHT" in source
    assert "FOOD_CATALOG_SIMPLIFICATION_POSTFLIGHT" in source
    assert "FOOD_CATALOG_SIMPLIFICATION_DOWNGRADE_BLOCKED" in source
    assert "DELETE FROM food" not in source
    assert "DELETE FROM diary_entry" not in source
    assert "DROP TABLE" not in source
    assert "DROP COLUMN" not in source or "CASCADE" not in source


def test_food_catalog_unification_migration_replaces_archive_and_fk_contracts() -> None:
    source = migration_source()

    for retired in (
        "ck_food_archive_state",
        "fk_food_archived_by_principal",
        "ix_food_catalog_primary_archived",
        "archived_by_principal_id",
        "archived_at",
    ):
        assert retired in source
    assert 'ondelete="CASCADE"' in source
    assert "ix_food_catalog_primary_category" in source
    assert "REVOKE ALL PRIVILEGES ON TABLE public.food FROM PUBLIC" in source
    assert "ARRAY['anon', 'authenticated']" in source


def test_food_catalog_unification_migration_preserves_unrelated_domains() -> None:
    source = migration_source()

    for protected in (
        "target_plan",
        "idempotency_record",
        "calculation_document",
    ):
        assert f'DROP TABLE {protected}' not in source
        assert f'DELETE FROM {protected}' not in source
