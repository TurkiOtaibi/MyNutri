from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session

from app.db.session import engine
from app.nutrition_rules.registry import FOOD_CATEGORIES


def proposed_mappings(session: Session) -> list[dict[str, Any]]:
    rows = session.connection().execute(
        text(
            "SELECT f.id,f.name,f.food_category_key,f.grain_type,f.baked_good_type,"
            "f.grain_starch_type,f.taxonomy_review_required,a.legacy_category,"
            "a.legacy_primary_category_key FROM food f JOIN food_taxonomy_v2_migration_audit a "
            "ON a.food_id=f.id WHERE f.taxonomy_review_required=true ORDER BY f.id"
        )
    ).mappings()
    return [
        {
            **dict(row),
            "id": str(row["id"]),
            "resolution": None,
            "reason": "ambiguous_requires_human_review",
        }
        for row in rows
    ]


def apply_reviewed_mapping(session: Session, mappings: list[dict[str, Any]]) -> None:
    allowed = set(FOOD_CATEGORIES)
    for item in mappings:
        food_id = UUID(str(item["id"]))
        category = item.get("food_category_key")
        if category not in allowed:
            raise RuntimeError(f"Invalid food_category_key for {food_id}.")
        grain_type = item.get("grain_type")
        baked_type = item.get("baked_good_type")
        starch_type = item.get("grain_starch_type")
        if category == "baked_goods" and (not grain_type or not baked_type or starch_type):
            raise RuntimeError(f"Incomplete baked-goods mapping for {food_id}.")
        if category == "grains_starches" and (not grain_type or not starch_type or baked_type):
            raise RuntimeError(f"Incomplete grains/starches mapping for {food_id}.")
        if category not in {"baked_goods", "grains_starches"} and any(
            value is not None for value in (grain_type, baked_type, starch_type)
        ):
            raise RuntimeError(f"Unrelated category detail for {food_id}.")
        result = session.connection().execute(
            text(
                "UPDATE food SET food_category_key=:category,grain_type=:grain_type,"
                "baked_good_type=:baked_type,grain_starch_type=:starch_type,"
                "taxonomy_review_required=false WHERE id=:food_id AND taxonomy_review_required=true"
            ),
            {
                "food_id": food_id,
                "category": category,
                "grain_type": grain_type,
                "baked_type": baked_type,
                "starch_type": starch_type,
            },
        )
        if result.rowcount != 1:
            raise RuntimeError(f"Food {food_id} is missing or already reviewed.")
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Review ambiguous Food Taxonomy V2 records.")
    parser.add_argument("--output", type=Path, default=Path("food-taxonomy-v2-review.json"))
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with Session(engine) as session:
        if args.apply:
            if args.mapping is None:
                raise RuntimeError("--mapping is required with --apply.")
            apply_reviewed_mapping(session, json.loads(args.mapping.read_text(encoding="utf-8")))
            print("Reviewed taxonomy mappings applied.")
        else:
            args.output.write_text(
                json.dumps(proposed_mappings(session), ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            print(f"Dry-run review written to {args.output}.")


if __name__ == "__main__":
    main()
