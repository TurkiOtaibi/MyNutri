from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlmodel import Session

from app.db.session import engine
from app.core.auth import PrincipalContext
from app.models import Food
from app.schemas import FoodCreate
from app.services.food import create_food, duplicate_key, list_foods, to_food_response

TARGET_DATABASE = "mynutri_dev"

UNIT_TYPE_MAP = {
    "حصة": "serving",
    "شريحة": "slice",
    "حبة": "piece",
    "قطعة": "piece",
}

QUALITY_PREFIX_MAP = {
    "label_direct": "جودة البيانات: مباشرة من الملصق",
    "label_derived": "جودة البيانات: مشتقة من الملصق",
    "label_derived_corrected": "جودة البيانات: مشتقة من الملصق بعد تصحيح",
    "label_derived_user_corrected": "جودة البيانات: مشتقة من الملصق مع تصحيحات المستخدم",
    "estimated": "جودة البيانات: تقديرية",
    "standard_estimate": "جودة البيانات: تقدير قياسي",
}

DIRECT_FIELDS = {
    "calories": "calories",
    "protein_g": "protein_g",
    "carbohydrates_g": "carb_g",
    "fat_g": "fat_g",
    "fiber_g": "fiber_g",
    "total_sugar_g": "sugar_g",
    "added_sugar_g": "added_sugar_g",
    "saturated_fat_g": "saturated_fat_g",
    "trans_fat_g": "trans_fat_g",
    "sodium_mg": "sodium_mg",
    "cholesterol_mg": "cholesterol_mg",
    "potassium_mg": "potassium_mg",
    "calcium_mg": "calcium_mg",
    "iron_mg": "iron_mg",
    "magnesium_mg": "magnesium_mg",
    "zinc_mg": "zinc_mg",
    "vitamin_d_mcg": "vitamin_d_mcg",
    "vitamin_b12_mcg": "vitamin_b12_mcg",
    "vitamin_c_mg": "vitamin_c_mg",
    "vitamin_a_mcg": "vitamin_a_mcg",
    "folate_mcg": "folate_mcg",
    "vitamin_k_mcg": "vitamin_k_mcg",
}

NUTRITION_FIELDS = tuple(DIRECT_FIELDS.values())

# Independent default-unit values explicitly stated in source notes.
EXPECTED_UNIT_VALUES: dict[str, dict[str, float]] = {
    "كيتو كوكيز بالشوكولاتة - KEO": {"calories": 80, "fat_g": 8},
    "توست البر - لوزين": {"calories": 77},
    "بسكويت رونديتاس بالشوكولاتة الداكنة بدون سكر - Gullón": {"calories": 31.8},
    "ويفر كابريس محشو بالشوكولاتة - Papadopoulos": {"calories": 28},
    "بسكويت أوريو ميني - Oreo Minis": {"calories": 140 / 9},
    "بسكويت الشوفان بالشوكولاتة الداكنة بدون سكر - Gullón Oaty": {"calories": 69},
    "بسكويت رقائق الشوكولاتة بدون سكر - Gullón Chip Choc": {"calories": 96},
    "بسكويت مغطى بالشوكولاتة الداكنة بدون سكر مضاف - Gullón Choc Tablet": {"calories": 63.5},
    "زبادي كامل الدسم - المراعي": {
        "calories": 120,
        "protein_g": 7,
        "carb_g": 10.5,
        "fat_g": 5.5,
        "sugar_g": 10.5,
    },
    "شرائح جبنة برجر كاملة الدسم - المراعي": {"calories": 56, "calcium_mg": 103.3},
    "شاورما عربي مع تغميسة ثوم": {
        "calories": 179,
        "protein_g": 8.5,
        "carb_g": 13.2,
        "fat_g": 10.2,
    },
    "بطاطس مقلية - حبة واحدة": {
        "calories": 13,
        "protein_g": 0.15,
        "carb_g": 1.6,
        "fat_g": 0.65,
    },
    "بيض مسلوق": {"calories": 78, "protein_g": 6.3, "carb_g": 0.6, "fat_g": 5.3},
}


class MappingDecisionNeeded(ValueError):
    pass


@dataclass
class ImportResult:
    name: str
    status: str
    reason: str
    food_id: str | None
    payload: dict[str, Any] | None
    unit_values: dict[str, float | None] | None
    unit_checks: list[dict[str, Any]]


def quality_notes(record: dict[str, Any]) -> str | None:
    quality = record.get("data_quality")
    if quality not in QUALITY_PREFIX_MAP:
        raise ValueError(f"Unsupported data_quality: {quality!r}")
    notes = record.get("notes")
    prefix = QUALITY_PREFIX_MAP[quality]
    return f"{prefix}. {notes}" if notes else f"{prefix}."


def map_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("nutrition_basis_amount") != 100 or record.get("nutrition_basis_unit") != "g":
        raise ValueError("Only nutrition values per 100 g are supported by this batch importer.")

    unit_name = record.get("default_unit_name")
    if unit_name == "علبة":
        raise MappingDecisionNeeded(
            "Default unit 'علبة' is unsupported. Decision Needed: add container or explicitly map it to serving."
        )
    if unit_name not in UNIT_TYPE_MAP:
        raise ValueError(f"Unsupported default unit name: {unit_name!r}")

    payload: dict[str, Any] = {
        "name": record.get("name"),
        "brand": None,
        "category": None,
        "nutrition_basis": "per_100g",
        "default_unit_type": UNIT_TYPE_MAP[unit_name],
        "unit_amount": record.get("default_unit_amount"),
        "unit_basis": record.get("default_unit_base"),
        "notes": quality_notes(record),
        "data_source": record.get("data_source"),
    }
    for source, target in DIRECT_FIELDS.items():
        payload[target] = record[source] if source in record else None
    return payload


def calculate_unit_values(payload: dict[str, Any]) -> dict[str, float | None]:
    factor = float(payload["unit_amount"]) / 100
    return {
        field: None if payload.get(field) is None else round(float(payload[field]) * factor, 4)
        for field in NUTRITION_FIELDS
    }


def validate_unit_values(name: str, values: dict[str, float | None], tolerance: float = 0.06) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for field, expected in EXPECTED_UNIT_VALUES.get(name, {}).items():
        actual = values[field]
        difference = None if actual is None else abs(actual - expected)
        checks.append(
            {
                "field": field,
                "expected": expected,
                "calculated": actual,
                "difference": difference,
                "passed": difference is not None and difference <= tolerance,
            }
        )
    return checks


def existing_by_key(
    session: Session, principal: PrincipalContext
) -> dict[tuple[str, str, str, float, str], Food]:
    return {
        duplicate_key(to_food_response(food).model_dump()): food
        for food in list_foods(session, principal)
    }


def validate_target_database(session: Session) -> str:
    database_name = session.exec(text("SELECT current_database()")).one()[0]
    if database_name != TARGET_DATABASE:
        raise RuntimeError(
            f"Refusing import into {database_name!r}; expected local/dev database {TARGET_DATABASE!r}."
        )
    return str(database_name)


def dry_run(
    session: Session, principal: PrincipalContext, dataset: dict[str, Any]
) -> list[ImportResult]:
    foods = dataset.get("foods")
    if not isinstance(foods, list) or dataset.get("record_count") != len(foods):
        raise ValueError("Dataset record_count does not match the foods array.")

    current = existing_by_key(session, principal)
    batch_keys: set[tuple[str, str, str, float, str]] = set()
    results: list[ImportResult] = []
    for record in foods:
        name = str(record.get("name", ""))
        try:
            mapped = map_record(record)
            payload = FoodCreate.model_validate(mapped)
            payload_data = payload.model_dump(exclude={"id"}, mode="json")
            key = duplicate_key(payload_data)
            unit_values = calculate_unit_values(payload_data)
            unit_checks = validate_unit_values(payload.name, unit_values)
            failed_checks = [check for check in unit_checks if not check["passed"]]
            if failed_checks:
                results.append(
                    ImportResult(name, "failed_validation", "Default-unit calculation mismatch.", None, payload_data, unit_values, unit_checks)
                )
            elif key in current:
                results.append(
                    ImportResult(name, "duplicate", "Matches an existing Food duplicate key.", str(current[key].id), payload_data, unit_values, unit_checks)
                )
            elif key in batch_keys:
                results.append(
                    ImportResult(name, "duplicate", "Duplicates an earlier record in this batch.", None, payload_data, unit_values, unit_checks)
                )
            else:
                batch_keys.add(key)
                results.append(ImportResult(name, "valid", "Validated and ready to import.", None, payload_data, unit_values, unit_checks))
        except MappingDecisionNeeded as error:
            results.append(ImportResult(name, "blocked_decision", str(error), None, None, None, []))
        except (ValidationError, ValueError) as error:
            results.append(ImportResult(name, "failed_validation", str(error), None, None, None, []))
    return results


def apply_import(
    session: Session, principal: PrincipalContext, dataset: dict[str, Any]
) -> list[ImportResult]:
    results = dry_run(session, principal, dataset)
    for result in results:
        if result.status != "valid" or result.payload is None:
            continue
        try:
            food = create_food(session, principal, FoodCreate.model_validate(result.payload))
            result.status = "inserted"
            result.reason = "Created through the existing Food service."
            result.food_id = str(food.id)
        except HTTPException as error:
            if error.status_code == 422:
                duplicate = existing_by_key(session, principal).get(duplicate_key(result.payload))
                result.status = "duplicate"
                result.reason = "Matched an existing Food during insertion."
                result.food_id = str(duplicate.id) if duplicate else None
            else:
                raise
    return results


def load_dataset(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validate and import myNutri Foods batch 001.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--principal-id", required=True, type=UUID)
    parser.add_argument("--apply", action="store_true", help="Insert valid, non-duplicate records.")
    parser.add_argument("--output", type=Path, help="Optional JSON result file.")
    args = parser.parse_args()

    dataset = load_dataset(args.input)
    principal = PrincipalContext(args.principal_id)
    with Session(engine) as session:
        database = validate_target_database(session)
        results = (
            apply_import(session, principal, dataset)
            if args.apply
            else dry_run(session, principal, dataset)
        )

    output = {
        "database": database,
        "mode": "apply" if args.apply else "dry-run",
        "summary": {
            status: sum(result.status == status for result in results)
            for status in sorted({result.status for result in results})
        },
        "results": [asdict(result) for result in results],
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
