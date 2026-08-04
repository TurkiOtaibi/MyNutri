from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlmodel import Session

from app.db.session import engine
from app.models import Food, FoodTaxonomyV2MigrationAudit
from app.nutrition_rules.registry import (
    BAKED_GOOD_TYPE_DEFINITIONS,
    FOOD_CATEGORIES,
    GRAIN_STARCH_TYPE_DEFINITIONS,
    GRAIN_TYPE_DEFINITIONS,
)
from app.schemas import FoodCreate


REVIEW_REASON = "ambiguous_requires_human_review"
CONTEXT_KEYS = frozenset(
    {
        "id",
        "name",
        "food_category_key",
        "grain_type",
        "baked_good_type",
        "grain_starch_type",
        "taxonomy_review_required",
        "legacy_category",
        "legacy_primary_category_key",
        "resolution",
        "reason",
    }
)
RESOLUTION_KEYS = frozenset(
    {"food_category_key", "grain_type", "baked_good_type", "grain_starch_type"}
)


@dataclass(frozen=True)
class TaxonomyValues:
    food_category_key: str
    grain_type: str | None
    baked_good_type: str | None
    grain_starch_type: str | None


@dataclass(frozen=True)
class ReviewedMapping:
    food_id: UUID
    name: str
    context: TaxonomyValues
    taxonomy_review_required: bool
    legacy_category: str | None
    legacy_primary_category_key: str | None
    resolution: TaxonomyValues


def _definition_keys(definitions: tuple[dict[str, str], ...]) -> frozenset[str]:
    return frozenset(definition["key"] for definition in definitions)


def _require_exact_keys(value: dict[str, Any], expected: frozenset[str], label: str) -> None:
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise RuntimeError(f"Invalid {label} keys; missing={missing}, unknown={unknown}.")


def _require_nullable_string(value: Any, field: str, food_id: UUID) -> str | None:
    if value is not None and not isinstance(value, str):
        raise RuntimeError(f"Invalid {field} type for {food_id}.")
    return value


def _taxonomy_values(value: dict[str, Any], food_id: UUID, label: str) -> TaxonomyValues:
    _require_exact_keys(value, RESOLUTION_KEYS, label)
    category = value["food_category_key"]
    if not isinstance(category, str):
        raise RuntimeError(f"Invalid food_category_key type for {food_id}.")
    return TaxonomyValues(
        food_category_key=category,
        grain_type=_require_nullable_string(value["grain_type"], "grain_type", food_id),
        baked_good_type=_require_nullable_string(
            value["baked_good_type"], "baked_good_type", food_id
        ),
        grain_starch_type=_require_nullable_string(
            value["grain_starch_type"], "grain_starch_type", food_id
        ),
    )


def _validate_resolution(mapping: ReviewedMapping) -> None:
    resolution = mapping.resolution
    food_id = mapping.food_id
    if resolution.food_category_key not in FOOD_CATEGORIES:
        raise RuntimeError(f"Invalid food_category_key for {food_id}.")
    allowed_details = {
        "grain_type": _definition_keys(GRAIN_TYPE_DEFINITIONS),
        "baked_good_type": _definition_keys(BAKED_GOOD_TYPE_DEFINITIONS),
        "grain_starch_type": _definition_keys(GRAIN_STARCH_TYPE_DEFINITIONS),
    }
    for field, allowed in allowed_details.items():
        value = getattr(resolution, field)
        if value is not None and value not in allowed:
            raise RuntimeError(f"Invalid {field} for {food_id}.")
    try:
        FoodCreate.model_validate(
            {
                "name": mapping.name,
                "food_category_key": resolution.food_category_key,
                "grain_type": resolution.grain_type,
                "baked_good_type": resolution.baked_good_type,
                "grain_starch_type": resolution.grain_starch_type,
                "nutrition_basis": "per_100g",
                "default_unit_type": "g",
                "unit_amount": 100,
                "unit_basis": "g",
                "calories": 0,
                "protein_g": 0,
                "carb_g": 0,
                "fat_g": 0,
            }
        )
    except ValidationError as exc:
        raise RuntimeError(f"Incompatible taxonomy resolution for {food_id}.") from exc


def parse_reviewed_mappings(mappings: Any) -> list[ReviewedMapping]:
    if not isinstance(mappings, list):
        raise RuntimeError("Reviewed taxonomy mapping root must be a list.")
    if not mappings:
        raise RuntimeError(
            "Reviewed taxonomy mapping must contain at least one explicit resolution."
        )
    parsed: list[ReviewedMapping] = []
    seen_ids: set[UUID] = set()
    for index, item in enumerate(mappings):
        if not isinstance(item, dict):
            raise RuntimeError(f"Reviewed taxonomy row {index} must be an object.")
        _require_exact_keys(item, CONTEXT_KEYS, f"reviewed taxonomy row {index}")
        try:
            food_id = UUID(str(item["id"]))
        except (TypeError, ValueError, AttributeError) as exc:
            raise RuntimeError(f"Invalid Food UUID at row {index}.") from exc
        if food_id in seen_ids:
            raise RuntimeError(f"Duplicate Food UUID {food_id}.")
        seen_ids.add(food_id)
        if not isinstance(item["name"], str):
            raise RuntimeError(f"Invalid name type for {food_id}.")
        if type(item["taxonomy_review_required"]) is not bool:
            raise RuntimeError(f"Invalid taxonomy_review_required type for {food_id}.")
        if item["reason"] != REVIEW_REASON:
            raise RuntimeError(f"Invalid review reason for {food_id}.")
        resolution = item["resolution"]
        if not isinstance(resolution, dict):
            raise RuntimeError(f"Explicit resolution object required for {food_id}.")
        mapping = ReviewedMapping(
            food_id=food_id,
            name=item["name"],
            context=_taxonomy_values(
                {key: item[key] for key in RESOLUTION_KEYS}, food_id, "context"
            ),
            taxonomy_review_required=item["taxonomy_review_required"],
            legacy_category=_require_nullable_string(
                item["legacy_category"], "legacy_category", food_id
            ),
            legacy_primary_category_key=_require_nullable_string(
                item["legacy_primary_category_key"],
                "legacy_primary_category_key",
                food_id,
            ),
            resolution=_taxonomy_values(resolution, food_id, "resolution"),
        )
        _validate_resolution(mapping)
        parsed.append(mapping)
    return sorted(parsed, key=lambda mapping: mapping.food_id)


def proposed_mappings(session: Session) -> list[dict[str, Any]]:
    statement = (
        select(
            Food.id,
            Food.name,
            Food.food_category_key,
            Food.grain_type,
            Food.baked_good_type,
            Food.grain_starch_type,
            Food.taxonomy_review_required,
            FoodTaxonomyV2MigrationAudit.legacy_category,
            FoodTaxonomyV2MigrationAudit.legacy_primary_category_key,
        )
        .join(FoodTaxonomyV2MigrationAudit, FoodTaxonomyV2MigrationAudit.food_id == Food.id)
        .where(Food.taxonomy_review_required.is_(True))
        .order_by(Food.id)
    )
    rows = session.execute(statement).mappings()
    return [
        {
            **dict(row),
            "id": str(row["id"]),
            "resolution": None,
            "reason": REVIEW_REASON,
        }
        for row in rows
    ]


def publish_review_export(output: Path, mappings: list[dict[str, Any]]) -> None:
    serialized = (
        json.dumps(mappings, ensure_ascii=False, indent=2, default=str) + "\n"
    )
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    descriptor_open = True
    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as temporary_file:
            descriptor_open = False
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        try:
            os.link(temporary_path, output)
        except FileExistsError as exc:
            raise RuntimeError(
                f"Taxonomy review export already exists: {output.name}."
            ) from exc
    finally:
        if descriptor_open:
            os.close(file_descriptor)
        temporary_path.unlink(missing_ok=True)


def _assert_current_context(current: dict[str, Any], mapping: ReviewedMapping) -> None:
    expected = {
        "name": mapping.name,
        "food_category_key": mapping.context.food_category_key,
        "grain_type": mapping.context.grain_type,
        "baked_good_type": mapping.context.baked_good_type,
        "grain_starch_type": mapping.context.grain_starch_type,
        "taxonomy_review_required": mapping.taxonomy_review_required,
        "legacy_category": mapping.legacy_category,
        "legacy_primary_category_key": mapping.legacy_primary_category_key,
    }
    actual = {key: current[key] for key in expected}
    if actual != expected or not current["taxonomy_review_required"]:
        raise RuntimeError(f"Stale taxonomy review context for {mapping.food_id}.")


def apply_reviewed_mapping(session: Session, mappings: Any) -> dict[str, Any]:
    try:
        reviewed = parse_reviewed_mappings(mappings)
        by_id = {mapping.food_id: mapping for mapping in reviewed}
        food_ids = list(by_id)
        statement = (
            select(
                Food.id,
                Food.name,
                Food.food_category_key,
                Food.grain_type,
                Food.baked_good_type,
                Food.grain_starch_type,
                Food.taxonomy_review_required,
                FoodTaxonomyV2MigrationAudit.food_id.label("audit_food_id"),
                FoodTaxonomyV2MigrationAudit.legacy_category,
                FoodTaxonomyV2MigrationAudit.legacy_primary_category_key,
            )
            .outerjoin(
                FoodTaxonomyV2MigrationAudit,
                FoodTaxonomyV2MigrationAudit.food_id == Food.id,
            )
            .where(Food.id.in_(food_ids))
            .order_by(Food.id)
            .with_for_update(of=Food)
        )
        current_rows = session.execute(statement).mappings().all() if food_ids else []
        if len(current_rows) != len(reviewed):
            found_ids = {row["id"] for row in current_rows}
            missing = [str(food_id) for food_id in food_ids if food_id not in found_ids]
            raise RuntimeError(f"Missing taxonomy review Foods: {missing}.")
        for current in current_rows:
            if current["audit_food_id"] is None:
                raise RuntimeError(f"Missing taxonomy review audit for {current['id']}.")
            _assert_current_context(dict(current), by_id[current["id"]])
        for mapping in reviewed:
            resolution = mapping.resolution
            result = session.execute(
                update(Food)
                .where(Food.id == mapping.food_id, Food.taxonomy_review_required.is_(True))
                .values(
                    food_category_key=resolution.food_category_key,
                    grain_type=resolution.grain_type,
                    baked_good_type=resolution.baked_good_type,
                    grain_starch_type=resolution.grain_starch_type,
                    taxonomy_review_required=False,
                )
            )
            if result.rowcount != 1:
                raise RuntimeError(f"Stale taxonomy review context for {mapping.food_id}.")
        session.commit()
        return {
            "applied_count": len(reviewed),
            "food_ids": [str(item.food_id) for item in reviewed],
        }
    except Exception:
        session.rollback()
        raise


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
            publish_review_export(args.output, proposed_mappings(session))
            print(f"Dry-run review written to {args.output.name}.")


if __name__ == "__main__":
    main()
