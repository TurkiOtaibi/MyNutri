"""simplify Food and retire snapshots and analysis features

Revision ID: f47a2c9d6e13
Revises: 8a91c4e7d2f6
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from alembic.util import CommandError

revision: str = "f47a2c9d6e13"
down_revision: str | None = "8a91c4e7d2f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FOOD_TAXONOMY: dict[str, tuple[str, ...]] = {
    "grains_and_starches": (
        "rice",
        "oats",
        "pasta",
        "bulgur",
        "jareesh",
        "wheat",
        "barley",
        "corn",
        "potatoes",
        "sweet_potatoes",
        "other",
    ),
    "bakery": (
        "bread",
        "toast",
        "samoli",
        "croissant",
        "pastries",
        "tortilla_and_wraps",
        "biscuits_and_crackers",
        "other",
    ),
    "meat_and_poultry": (
        "chicken",
        "turkey",
        "beef",
        "lamb",
        "camel",
        "eggs",
        "processed_meat",
        "other",
    ),
    "fish_and_seafood": (
        "fish",
        "tuna",
        "shrimp",
        "crustaceans",
        "mollusks",
        "other",
    ),
    "dairy_products": (
        "milk",
        "laban",
        "yogurt",
        "labneh",
        "cheese",
        "cream_and_qishta",
        "other",
    ),
    "legumes": (
        "lentils",
        "chickpeas",
        "beans",
        "fava_beans",
        "peas",
        "cowpeas",
        "lupin",
        "other",
    ),
    "vegetables": (
        "leafy_vegetables",
        "cruciferous_vegetables",
        "root_vegetables",
        "tomatoes",
        "cucumber",
        "peppers",
        "onion_and_garlic",
        "zucchini_and_squash",
        "eggplant",
        "mushrooms",
        "other",
    ),
    "fruits": (
        "citrus",
        "apples_and_pears",
        "bananas",
        "grapes",
        "berries",
        "stone_fruits",
        "tropical_fruits",
        "watermelon_and_melon",
        "dates",
        "pomegranate",
        "figs",
        "dried_fruits",
        "other",
    ),
    "nuts_and_seeds": (
        "almonds",
        "walnuts",
        "cashews",
        "pistachios",
        "hazelnuts",
        "peanuts",
        "sesame_seeds",
        "chia_seeds",
        "flax_seeds",
        "sunflower_seeds",
        "pumpkin_seeds",
        "other",
    ),
    "fats_and_oils": (
        "olive_oil",
        "vegetable_oils",
        "coconut_oil",
        "butter",
        "ghee",
        "margarine",
        "other",
    ),
    "sweets_and_sugars": (
        "cake",
        "chocolate",
        "sweet_biscuits",
        "middle_eastern_sweets",
        "western_desserts",
        "ice_cream_and_frozen_desserts",
        "candy",
        "sugar_and_sweeteners",
        "jam_and_sweet_spreads",
        "other",
    ),
    "beverages": (
        "water",
        "coffee",
        "tea",
        "juices",
        "carbonated_drinks",
        "energy_drinks",
        "sports_drinks",
        "plant_based_drinks",
        "shakes_and_smoothies",
        "other",
    ),
    "meals": (
        "rice_dishes",
        "pasta_dishes",
        "burgers_and_sandwiches",
        "shawarma",
        "pizza",
        "salads",
        "soups",
        "main_dishes",
        "breakfast_meals",
        "other",
    ),
    "sauces_spices_and_additions": (
        "sauces",
        "mayonnaise",
        "dressings",
        "tahini",
        "spices_and_seasonings",
        "herbs",
        "salt",
        "vinegar",
        "additions",
        "other",
    ),
    "other": ("other",),
}

RETIRED_TABLES = (
    "behavior_goal_reminder_delivery",
    "behavior_goal_command_idempotency",
    "behavior_goal_history",
    "behavior_goal",
    "weekly_priority_evidence_ref",
    "weekly_priority_evaluation",
    "weekly_priority_recommendation",
    "nutrition_analysis_command_idempotency",
    "nutrition_analysis_revision_event",
    "nutrition_analysis_evidence_ref",
    "nutrition_analysis_revision",
    "nutrition_analysis",
    "food_analytical_trait",
    "food_group_contribution",
)


def _quoted(values: Sequence[str]) -> str:
    return ",".join(f"'{value}'" for value in values)


def _taxonomy_pair_constraint() -> str:
    return " OR ".join(
        f"(primary_category='{primary}' AND subcategory IN ({_quoted(children)}))"
        for primary, children in FOOD_TAXONOMY.items()
    )


def _retired_data_preflight() -> None:
    unions = " UNION ALL ".join(
        f"SELECT '{table}' AS table_name, count(*) AS row_count FROM {table}"
        for table in RETIRED_TABLES
    )
    op.execute(
        f"""
        DO $$
        DECLARE populated jsonb;
        BEGIN
          SELECT jsonb_object_agg(table_name, row_count) INTO populated
          FROM ({unions}) AS counts WHERE row_count > 0;
          IF populated IS NOT NULL THEN
            RAISE EXCEPTION
              'FOOD_SIMPLIFICATION_RETIRED_DATA_CLEANUP_REQUIRED: %', populated
              USING ERRCODE = 'check_violation';
          END IF;
        END
        $$;
        """
    )


def _migrate_food() -> None:
    op.add_column("food", sa.Column("primary_category", sa.Text(), nullable=True))
    op.add_column("food", sa.Column("subcategory", sa.Text(), nullable=True))
    op.add_column(
        "food",
        sa.Column(
            "nutrition_data_source",
            sa.Text(),
            nullable=True,
            server_default="estimated",
        ),
    )
    op.add_column("food", sa.Column("ingredients", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE food SET
          primary_category = CASE food_category_key
            WHEN 'grains_starches' THEN 'grains_and_starches'
            WHEN 'baked_goods' THEN 'bakery'
            WHEN 'poultry' THEN 'meat_and_poultry'
            WHEN 'red_meat' THEN 'meat_and_poultry'
            WHEN 'processed_meat' THEN 'meat_and_poultry'
            WHEN 'eggs' THEN 'meat_and_poultry'
            WHEN 'seafood' THEN 'fish_and_seafood'
            WHEN 'dairy_fortified_alternatives' THEN 'dairy_products'
            WHEN 'legumes' THEN 'legumes'
            WHEN 'vegetables' THEN 'vegetables'
            WHEN 'fruits' THEN 'fruits'
            WHEN 'nuts_seeds' THEN 'nuts_and_seeds'
            WHEN 'added_oils_fats' THEN 'fats_and_oils'
            WHEN 'sweets' THEN 'sweets_and_sugars'
            WHEN 'sugar_sweetened_beverages' THEN 'beverages'
            WHEN 'unsweetened_beverages' THEN 'beverages'
            WHEN 'mixed_dish' THEN 'meals'
            WHEN 'herbs_spices' THEN 'sauces_spices_and_additions'
            ELSE 'other'
          END,
          subcategory = CASE
            WHEN food_category_key='grains_starches' AND grain_starch_type IN
              ('rice','pasta','oats','bulgur') THEN grain_starch_type
            WHEN food_category_key='baked_goods' AND baked_good_type='toast' THEN 'toast'
            WHEN food_category_key='baked_goods' AND baked_good_type='pastries' THEN 'pastries'
            WHEN food_category_key='baked_goods' AND baked_good_type='biscuits_cookies'
              THEN 'biscuits_and_crackers'
            WHEN food_category_key='baked_goods' AND baked_good_type IN
              ('arabic_bread','flatbread') THEN 'bread'
            WHEN food_category_key='baked_goods' AND baked_good_type='rolls_wraps'
              THEN 'tortilla_and_wraps'
            WHEN food_category_key='eggs' THEN 'eggs'
            WHEN food_category_key='processed_meat' THEN 'processed_meat'
            ELSE 'other'
          END,
          nutrition_data_source = CASE
            WHEN nutrition_source_type='official_product_label' THEN 'official'
            ELSE 'estimated'
          END,
          ingredients = ingredients_text
        """
    )
    op.alter_column("food", "primary_category", existing_type=sa.Text(), nullable=False)
    op.alter_column("food", "subcategory", existing_type=sa.Text(), nullable=False)
    op.alter_column("food", "nutrition_data_source", existing_type=sa.Text(), nullable=False)

    op.drop_index("ix_food_catalog_category_status", table_name="food")
    for constraint in (
        "ck_food_category_details_v2",
        "ck_food_grain_starch_type",
        "ck_food_baked_good_type",
        "ck_food_grain_type",
        "ck_food_category_v2",
        "ck_food_status",
        "ck_food_archive_state",
        "ck_food_kind",
        "ck_food_group_data_status",
        "ck_food_group_data_completeness",
        "ck_food_nutrition_source_type",
        "ck_food_ingredients_source_type",
        "ck_food_nova_classification",
        "ck_food_nova_review_status",
    ):
        op.drop_constraint(constraint, "food", type_="check")

    for column in (
        "food_category_key",
        "grain_type",
        "baked_good_type",
        "grain_starch_type",
        "taxonomy_review_required",
        "status",
        "food_kind",
        "group_data_status",
        "group_data_completeness",
        "data_source",
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
        op.drop_column("food", column)

    op.create_check_constraint(
        "ck_food_primary_category",
        "food",
        f"primary_category IN ({_quoted(tuple(FOOD_TAXONOMY))})",
    )
    op.create_check_constraint(
        "ck_food_taxonomy_pair", "food", _taxonomy_pair_constraint()
    )
    op.create_check_constraint(
        "ck_food_archive_state",
        "food",
        "(archived_at IS NULL AND archived_by_principal_id IS NULL) OR "
        "(archived_at IS NOT NULL AND archived_by_principal_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_food_nutrition_data_source",
        "food",
        "nutrition_data_source IN ('official','estimated')",
    )
    op.create_index(
        "ix_food_catalog_primary_archived",
        "food",
        ["primary_category", "archived_at"],
    )


def _migrate_diary() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM diary_entry d
            LEFT JOIN food f ON f.id=d.food_id
            WHERE d.food_id IS NULL OR f.id IS NULL
          ) THEN
            RAISE EXCEPTION 'FOOD_SIMPLIFICATION_ORPHANED_DIARY_FOOD_REFERENCE'
              USING ERRCODE = 'foreign_key_violation';
          END IF;
        END $$;
        """
    )
    op.add_column("diary_entry", sa.Column("recorded_unit_type", sa.Text(), nullable=True))
    op.add_column(
        "diary_entry", sa.Column("recorded_unit_amount", sa.Numeric(10, 4), nullable=True)
    )
    op.add_column("diary_entry", sa.Column("recorded_unit_basis", sa.Text(), nullable=True))
    op.add_column(
        "diary_entry", sa.Column("recorded_unit_label", sa.String(80), nullable=True)
    )
    op.execute(
        """
        UPDATE diary_entry SET
          recorded_unit_type = CASE
            WHEN snapshot_schema_version IN (2,3,4)
              THEN nutrition_snapshot->'captured_unit'->>'default_unit_type'
            WHEN COALESCE(nutrition_snapshot->>'log_mode','servings')='grams'
              THEN CASE WHEN nutrition_snapshot->>'nutrition_basis'='per_100ml' THEN 'ml' ELSE 'g' END
            ELSE COALESCE(
              nutrition_snapshot->>'default_unit_type',
              CASE WHEN nutrition_snapshot ? 'serving_grams' THEN 'serving' END
            )
          END,
          recorded_unit_amount = CASE
            WHEN snapshot_schema_version IN (2,3,4)
              THEN (nutrition_snapshot->'captured_unit'->>'unit_amount')::numeric
            WHEN COALESCE(nutrition_snapshot->>'log_mode','servings')='grams' THEN 1
            ELSE COALESCE(
              (nutrition_snapshot->>'unit_amount')::numeric,
              (nutrition_snapshot->>'serving_grams')::numeric
            )
          END,
          recorded_unit_basis = CASE
            WHEN snapshot_schema_version IN (2,3,4)
              THEN nutrition_snapshot->'captured_unit'->>'unit_basis'
            ELSE COALESCE(
              nutrition_snapshot->>'unit_basis',
              CASE WHEN nutrition_snapshot->>'nutrition_basis'='per_100ml' THEN 'ml'
                   WHEN nutrition_snapshot->>'nutrition_basis'='per_100g' THEN 'g' END
            )
          END,
          recorded_unit_label = NULLIF(nutrition_snapshot->>'serving_label','')
        """
    )
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM diary_entry
            WHERE recorded_unit_type NOT IN
              ('g','ml','cup','slice','piece','scoop','serving','tablespoon','teaspoon')
               OR recorded_unit_amount IS NULL OR recorded_unit_amount <= 0
               OR recorded_unit_amount IN ('NaN','Infinity','-Infinity')
               OR recorded_unit_basis NOT IN ('g','ml')
          ) THEN
            RAISE EXCEPTION 'FOOD_SIMPLIFICATION_DIARY_MEASUREMENT_BACKFILL_REQUIRED'
              USING ERRCODE = 'check_violation';
          END IF;
        END $$;
        """
    )
    op.alter_column("diary_entry", "recorded_unit_type", existing_type=sa.Text(), nullable=False)
    op.alter_column(
        "diary_entry", "recorded_unit_amount", existing_type=sa.Numeric(10, 4), nullable=False
    )
    op.alter_column("diary_entry", "recorded_unit_basis", existing_type=sa.Text(), nullable=False)

    op.execute("DROP TRIGGER diary_snapshot_binding_immutable_trigger ON diary_entry")
    op.execute("DROP FUNCTION protect_diary_snapshot_binding()")
    op.drop_constraint("ck_diary_entry_versioned_shape", "diary_entry", type_="check")
    op.drop_constraint("ck_diary_entry_snapshot_version", "diary_entry", type_="check")
    op.drop_column("diary_entry", "nutrition_snapshot")
    op.drop_column("diary_entry", "snapshot_schema_version")

    op.execute(
        """
        DO $$
        DECLARE constraint_name text;
        BEGIN
          FOR constraint_name IN
            SELECT c.conname FROM pg_constraint c
            WHERE c.contype='f'
              AND c.conrelid='diary_entry'::regclass
              AND c.confrelid='food'::regclass
          LOOP
            EXECUTE format('ALTER TABLE diary_entry DROP CONSTRAINT %I', constraint_name);
          END LOOP;
        END $$;
        """
    )
    op.alter_column("diary_entry", "food_id", existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key(
        "fk_diary_entry_food",
        "diary_entry",
        "food",
        ["food_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_diary_entry_recorded_unit_amount_positive_finite",
        "diary_entry",
        "recorded_unit_amount > 0 AND "
        "recorded_unit_amount NOT IN ('NaN','Infinity','-Infinity')",
    )
    op.create_check_constraint(
        "ck_diary_entry_recorded_unit_type",
        "diary_entry",
        "recorded_unit_type IN "
        "('g','ml','cup','slice','piece','scoop','serving','tablespoon','teaspoon')",
    )
    op.create_check_constraint(
        "ck_diary_entry_recorded_unit_basis",
        "diary_entry",
        "recorded_unit_basis IN ('g','ml')",
    )
    op.execute(
        """
        CREATE FUNCTION protect_diary_event_binding() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF NEW.entry_date IS DISTINCT FROM OLD.entry_date
             OR NEW.food_id IS DISTINCT FROM OLD.food_id
             OR NEW.principal_id IS DISTINCT FROM OLD.principal_id
             OR NEW.recorded_unit_type IS DISTINCT FROM OLD.recorded_unit_type
             OR NEW.recorded_unit_amount IS DISTINCT FROM OLD.recorded_unit_amount
             OR NEW.recorded_unit_basis IS DISTINCT FROM OLD.recorded_unit_basis
             OR NEW.recorded_unit_label IS DISTINCT FROM OLD.recorded_unit_label
          THEN RAISE EXCEPTION 'Diary event identity and measurement are immutable'
            USING ERRCODE='23514'; END IF;
          IF (NEW.target_plan_id IS DISTINCT FROM OLD.target_plan_id
              OR NEW.target_provenance IS DISTINCT FROM OLD.target_provenance)
             AND NOT (
               OLD.target_plan_id IS NULL
               AND OLD.target_provenance = 'no_target_source'
               AND NEW.target_plan_id IS NOT NULL
               AND NEW.target_provenance = 'versioned_plan'
             )
          THEN RAISE EXCEPTION 'Diary target binding is immutable'
            USING ERRCODE='23514'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER diary_event_binding_immutable_trigger BEFORE UPDATE ON diary_entry
          FOR EACH ROW EXECUTE FUNCTION protect_diary_event_binding();
        """
    )


def upgrade() -> None:
    _retired_data_preflight()
    op.execute("DROP SCHEMA nova_retirement CASCADE")
    _migrate_food()
    _migrate_diary()
    op.execute("DROP TABLE food_taxonomy_v2_migration_audit")
    op.execute("DROP TRIGGER food_group_contribution_total_trigger ON food_group_contribution")
    op.execute("DROP FUNCTION enforce_food_group_contribution_total()")
    for table in RETIRED_TABLES:
        op.execute(f"DROP TABLE {table} CASCADE")


def downgrade() -> None:
    message = (
        "FOOD_SIMPLIFICATION_RETIREMENT_DOWNGRADE_BLOCKED: the retired active-product "
        "schema and removed Food snapshots cannot be reconstructed without reintroducing "
        "obsolete contracts; roll forward or restore an approved backup"
    )
    if context.is_offline_mode():
        raise CommandError(f"{message}; offline downgrade SQL is intentionally unavailable")
    raise CommandError(message)
